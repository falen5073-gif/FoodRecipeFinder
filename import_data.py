# ==============================================================================
# SKRIP MIGRASI DATA RESEP KE DATABASE MYSQL (import_data.py)
# ==============================================================================
# Skrip ini bertugas membaca data resep lokal dari berkas recipes.json dan daftar
# favorit dari favorites.json, kemudian mengimpor serta menyinkronkannya ke dalam
# database MySQL / MariaDB (tabel recipes, ingredients, dan favorites).
# ==============================================================================

# ------------------------------------------------------------------------------
# BAGIAN 1: IMPORT LIBRARY DAN DEPENDENSI
# ------------------------------------------------------------------------------

# Library bawaan Python untuk membaca (decode) dan memproses file berformat JSON.
import json

# Modul Path dari library bawaan 'pathlib' untuk memanipulasi direktori dan lokasi file secara dinamis.
from pathlib import Path

# Library pihak ketiga (PyMySQL) sebagai database driver penghubung Python dengan MySQL / MariaDB.
import pymysql


# ------------------------------------------------------------------------------
# BAGIAN 2: KONFIGURASI DIREKTORI DAN KONEKSI DATABASE
# ------------------------------------------------------------------------------

# Menentukan direktori absolut tempat berkas skrip ini berada.
BASE_DIR = Path(__file__).resolve().parent

# Dictionary konfigurasi parameter autentikasi dan koneksi ke database MySQL.
DB_CONFIG = {
    # Alamat host server database MySQL lokal.
    "host": "localhost",
    # Username database default (biasanya 'root' pada lingkungan XAMPP/Laragon).
    "user": "root",
    # Password user database (dikosongkan jika menggunakan konfigurasi default lokal).
    "password": "",
    # Nama schema database target yang menyimpan tabel resep.
    "database": "food_recipe_finder",
    # Set karakter enkripsi UTF-8 multibyte (mendukung berbagai simbol dan emoji).
    "charset": "utf8mb4",
    # Tipe kursor kustom agar hasil query SELECT dikembalikan berupa dictionary (key: nama kolom).
    "cursorclass": pymysql.cursors.DictCursor,
}


# ------------------------------------------------------------------------------
# BAGIAN 3: FUNGSI UTILITAS DATA
# ------------------------------------------------------------------------------

# Fungsi untuk membaca dan memparsing berkas JSON secara aman dengan nilai fallback jika gagal.
def load_json(file_path, default):
    """Membaca file JSON jika tersedia."""
    # Memeriksa apakah file pada path yang diberikan benar-benar ada di penyimpanan.
    if not file_path.exists():
        # Mengembalikan nilai default jika file tidak ditemukan.
        return default

    # Membuka file dengan mode baca dan enkripsi UTF-8.
    with open(file_path, encoding="utf-8") as file:
        # Mengurai isi file menjadi struktur data Python (list/dict).
        return json.load(file)


# Fungsi untuk mengekstrak daftar kode ID resep favorit dari berbagai kemungkinan format struktur JSON.
def get_favorite_ids(data):
    """Mengambil ID favorit dari beberapa format JSON."""
    # Menangani jika struktur data berupa dictionary pembungkus.
    if isinstance(data, dict):
        # Jika terdapat kunci "favorites", ambil isinya.
        if "favorites" in data:
            data = data["favorites"]
        # Jika terdapat kunci "meals", ambil isinya.
        elif "meals" in data:
            data = data["meals"]
        # Jika dictionary biasa, ambil seluruh kumpulan nilainya (values).
        else:
            data = list(data.values())

    # Jika setelah diproses data bukan berupa list, kembalikan list kosong.
    if not isinstance(data, list):
        return []

    # Menyiapkan list untuk menampung ID favorit yang telah divalidasi.
    favorite_ids = []

    # Melakukan perulangan pada setiap item di dalam data favorit.
    for item in data:
        # Jika item bertipe dictionary (objek resep).
        if isinstance(item, dict):
            # Mencoba mengekstrak ID dari 'idMeal', jika tidak ada cari 'recipe_code', lalu cari 'id'.
            favorite_id = item.get(
                "idMeal",
                item.get("recipe_code", item.get("id"))
            )
        # Jika item langsung berupa nilai scalar (string atau integer ID).
        else:
            favorite_id = item

        # Memastikan ID tidak bernilai None dan bukan string kosong setelah di-strip.
        if favorite_id is not None and str(favorite_id).strip():
            # Menyimpan ID yang sudah dibersihkan ke dalam list penampung.
            favorite_ids.append(str(favorite_id).strip())

    # Mengembalikan daftar ID unik tanpa duplikasi dengan memanfaatkan dict.fromkeys.
    return list(dict.fromkeys(favorite_ids))


# ------------------------------------------------------------------------------
# BAGIAN 4: FUNGSI UTAMA PROSES MIGRASI DATA (main)
# ------------------------------------------------------------------------------

# Mendefinisikan fungsi utama alur migrasi database.
def main():
    # Membaca data resep dari berkas recipes.json pada BASE_DIR.
    recipes = load_json(BASE_DIR / "recipes.json", [])

    # Menangani jika resep dibungkus dalam dictionary dengan kunci "meals" atau "recipes".
    if isinstance(recipes, dict):
        recipes = recipes.get("meals", recipes.get("recipes", []))

    # Memvalidasi apakah recipes berformat list yang valid.
    if not isinstance(recipes, list):
        print("Error: format recipes.json harus berupa daftar resep.")
        return

    # Membaca data favorit dari berkas favorites.json pada BASE_DIR.
    favorites_data = load_json(BASE_DIR / "favorites.json", [])

    # Mengekstrak list ID favorit yang bersih dan terstandar.
    favorite_ids = get_favorite_ids(favorites_data)

    # Membuka koneksi aktif ke server database MySQL menggunakan parameter DB_CONFIG.
    connection = pymysql.connect(**DB_CONFIG)

    try:
        # Membuat kursor database untuk mengeksekusi perintah SQL.
        with connection.cursor() as cursor:

            # ------------------------------------------------------------------
            # TAHAP 1: Impor data resep dan bahan-bahan (ingredients)
            # ------------------------------------------------------------------
            for meal in recipes:
                # Mengambil kode unik resep dari field 'idMeal' atau 'recipe_code'.
                recipe_code = meal.get("idMeal", meal.get("recipe_code"))

                # Jika kode resep tidak ada, lewati resep ini dan lanjutkan ke resep berikutnya.
                if recipe_code is None:
                    print("Melewati resep tanpa ID.")
                    continue

                # Mengonversi kode resep ke tipe string untuk konsistensi query database.
                recipe_code = str(recipe_code)

                # Mengambil teks instruksi memasak dari 'instructions_list' atau 'strInstructions'.
                instructions = meal.get(
                    "instructions_list",
                    meal.get("strInstructions", "")
                )

                # Jika instruksi berupa list langkah-langkah, gabungkan menjadi string dengan baris baru.
                if isinstance(instructions, list):
                    instructions = "\n".join(map(str, instructions))

                # Mengeksekusi query INSERT atau UPDATE resep jika recipe_code sudah ada sebelumnya (UPSERT).
                cursor.execute("""
                    INSERT INTO recipes
                    (recipe_code, name, category, origin,
                     image_url, instructions)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    category = VALUES(category),
                    origin = VALUES(origin),
                    image_url = VALUES(image_url),
                    instructions = VALUES(instructions)
                """, (
                    recipe_code,
                    meal.get("strMeal", meal.get("name", "Resep tanpa nama")),
                    meal.get("strCategory", meal.get("category", "Lainnya")),
                    meal.get("strArea", meal.get("origin", "Indonesia")),
                    meal.get("strMealThumb", meal.get("image_url", "")),
                    instructions or "",
                ))

                # Mengambil ID primary key internal (auto-increment) dari tabel recipes berdasarkan recipe_code.
                cursor.execute(
                    "SELECT id FROM recipes WHERE recipe_code = %s",
                    (recipe_code,)
                )
                result = cursor.fetchone()

                # Jika data resep tidak ditemukan di database, lewati proses bahan.
                if not result:
                    continue

                # Mendapatkan integer ID resep pada database.
                recipe_id = result["id"]

                # Mengambil list bahan-bahan (ingredients) dari resep.
                ingredients = meal.get("ingredients", [])

                # Jika daftar bahan berupa list yang valid, lakukan sinkronisasi data bahan.
                if isinstance(ingredients, list):
                    # Menghapus bahan lama yang terasosiasi dengan recipe_id ini agar tidak terjadi duplikasi.
                    cursor.execute(
                        "DELETE FROM ingredients WHERE recipe_id = %s",
                        (recipe_id,)
                    )

                    # Melakukan iterasi untuk setiap item bahan.
                    for ingredient in ingredients:
                        # Memastikan item bahan bertipe dictionary.
                        if not isinstance(ingredient, dict):
                            continue

                        # Mengambil nama bahan.
                        ingredient_name = ingredient.get("name", "")
                        # Mengabaikan bahan jika nama bahannya kosong.
                        if not ingredient_name:
                            continue

                        # Menyimpan data bahan dan takarannya ke tabel ingredients.
                        cursor.execute("""
                            INSERT INTO ingredients
                            (recipe_id, name, measure)
                            VALUES (%s, %s, %s)
                        """, (
                            recipe_id,
                            ingredient_name,
                            ingredient.get("measure", ""),
                        ))

            # ------------------------------------------------------------------
            # TAHAP 2: Impor data resep favorit ke tabel favorites
            # ------------------------------------------------------------------
            # Menghitung jumlah favorit yang baru berhasil ditambahkan.
            imported_favorites = 0
            # Menyimpan daftar kode favorit yang belum terdaftar di tabel recipes.
            missing_favorites = []

            # Melakukan iterasi pada setiap ID favorit.
            for favorite_code in favorite_ids:
                # Mencari ID primary key dari tabel recipes berdasarkan kode resep favorit.
                cursor.execute(
                    "SELECT id FROM recipes WHERE recipe_code = %s",
                    (favorite_code,)
                )
                result = cursor.fetchone()

                # Jika resep ditemukan di database:
                if result:
                    # Masukkan ke tabel favorites; gunakan INSERT IGNORE untuk mengabaikan jika sudah pernah difavoritkan.
                    cursor.execute("""
                        INSERT IGNORE INTO favorites (recipe_id)
                        VALUES (%s)
                    """, (result["id"],))

                    # Jika ada baris baru yang berhasil dimasukkan, tambahkan penghitung.
                    if cursor.rowcount > 0:
                        imported_favorites += 1
                # Jika resep tidak ditemukan di database:
                else:
                    # Catat kode favorit yang hilang/tidak cocok ke dalam list missing_favorites.
                    missing_favorites.append(favorite_code)

        # Melakukan commit transaksi ke database agar seluruh perubahan disimpan secara permanen.
        connection.commit()

        # Menampilkan pesan log status penyelesaian proses migrasi ke konsol terminal.
        print(f"Berhasil memproses {len(recipes)} resep.")
        print(f"Favorit baru yang ditambahkan: {imported_favorites}")

        # Jika ada ID favorit yang tidak ditemukan di tabel resep, informasikan ke konsol.
        if missing_favorites:
            print(
                "ID favorit belum ditemukan di tabel recipes:",
                ", ".join(missing_favorites)
            )

        # Jika tidak ada satupun ID favorit yang terbaca dari favorites.json, beri peringatan format file.
        if not favorite_ids:
            print(
                "Tidak ada ID favorit yang terbaca. "
                "Periksa format favorites.json."
            )

    # Menangani error / exception tak terduga selama transaksi SQL berlangsung.
    except Exception as error:
        # Membatalkan (rollback) seluruh transaksi SQL jika terjadi kegagalan untuk menjaga konsistensi database.
        connection.rollback()
        # Mencetak pesan error ke konsol terminal.
        print(f"Terjadi error: {error}")

    # Blok finally akan selalu dieksekusi baik proses berhasil maupun gagal.
    finally:
        # Menutup koneksi database ke server MySQL agar tidak terjadi kebocoran koneksi (connection leak).
        connection.close()


# ------------------------------------------------------------------------------
# BAGIAN 5: ENTRY POINT EKSEKUSI SKRIP
# ------------------------------------------------------------------------------

# Memeriksa apakah skrip dieksekusi secara langsung dari terminal.
if __name__ == "__main__":
    # Menjalankan fungsi utama main().
    main()
