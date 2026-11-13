# ==============================================================================
# APLIKASI WEB FOOD RECIPE FINDER (app.py)
# ==============================================================================
# File ini merupakan server web utama berbasis Flask yang menangani:
# 1. Logika routing URL dan rendering template HTML.
# 2. Pembacaan koleksi resep lokal (recipes.json).
# 3. Makanan Favorit berdasarkan seberapa sering pengguna membuka menunya (favorites.json).
# 4. Fitur Simpan Menu / Bookmark Resep Pilihan pengguna (saved_menus.json).
# 5. Fitur pencarian resep dan penyaringan berdasarkan kategori.
# ==============================================================================

# ------------------------------------------------------------------------------
# BAGIAN 1: IMPORT LIBRARY DAN DEPENDENSI
# ------------------------------------------------------------------------------

# Library bawaan Python untuk membaca (decode) dan menulis (encode) format data JSON.
import json

# Library bawaan Python untuk berinteraksi dengan sistem operasi (misal membaca environment variable).
import os

# Library bawaan Python untuk operasi acak, digunakan untuk memilih resep acak (fitur "Surprise Me").
import random

# Library bawaan Python untuk mendeteksi rute koneksi jaringan dan alamat IP lokal komputer.
import socket

# Library bawaan Python untuk memformat tanggal dan waktu penyimpanan menu secara lokal.
from datetime import datetime

# Modul Path dari library bawaan 'pathlib' untuk mengelola path berkas dan folder secara aman lintas sistem operasi.
from pathlib import Path

# Mengimpor kelas dan fungsi esensial dari framework web Flask:
# - Flask: Kelas utama untuk membuat instance aplikasi web.
# - flash: Fungsi untuk mengirimkan pesan notifikasi sementara (kilat) ke pengguna.
# - redirect: Fungsi untuk mengalihkan pengguna ke URL atau endpoint lain.
# - render_template: Fungsi untuk memuat dan merender file template HTML menggunakan Jinja2.
# - request: Objek konteks global untuk membaca query parameter, data formulir POST, dan header request.
# - url_for: Fungsi pembantu untuk menghasilkan URL secara dinamis berdasarkan nama fungsi view.
from flask import Flask, flash, redirect, render_template, request, url_for

# ------------------------------------------------------------------------------
# BAGIAN 2: INISIALISASI DAN KONFIGURASI APLIKASI FLASK
# ------------------------------------------------------------------------------

# Menginisialisasi instance aplikasi Flask utama dengan modul saat ini (__name__).
app = Flask(__name__)

# Menetapkan kunci rahasia (secret key) untuk mengamankan data sesi dan flash message.
# Mengambil dari environment variable 'SECRET_KEY' jika tersedia, atau menggunakan kunci default lokal.
app.secret_key = os.environ.get(
    "SECRET_KEY", "food-recipe-finder-local-key"
)

# Menentukan path direktori dasar (base directory) tempat berkas app.py berada.
BASE_DIR = Path(__file__).resolve().parent

# Lokasi berkas basis data resep lokal (recipes.json).
RECIPES_FILE = BASE_DIR / "recipes.json"

# Lokasi berkas penyimpanan data makanan favorit berdasarkan frekuensi buka (favorites.json).
FAVORITES_FILE = BASE_DIR / "favorites.json"

# Lokasi berkas penyimpanan data fitur simpan menu / bookmark resep (saved_menus.json).
SAVED_MENUS_FILE = BASE_DIR / "saved_menus.json"


# ------------------------------------------------------------------------------
# BAGIAN 3: FUNGSI UTILITAS DATA DAN PENGOLAHAN RESEP
# ------------------------------------------------------------------------------

# Mendefinisikan fungsi untuk memuat seluruh koleksi resep lokal dari recipes.json.
def load_recipes():
    """Membaca koleksi resep lokal berbahasa Indonesia."""
    try:
        # Membuka berkas recipes.json dengan mode baca UTF-8.
        with RECIPES_FILE.open("r", encoding="utf-8") as file:
            recipes = json.load(file)

        # Memastikan data yang dibaca berupa list.
        if not isinstance(recipes, list):
            return []

        # Mengembalikan list resep yang telah distandardisasi dengan fungsi prepare_meal.
        return [
            prepare_meal(meal)
            for meal in recipes
            if isinstance(meal, dict) and meal.get("idMeal")
        ]

    # Mengembalikan list kosong jika berkas tidak ditemukan atau format JSON tidak valid.
    except (OSError, json.JSONDecodeError):
        return []


# Mendefinisikan fungsi pembantu untuk menstandarkan struktur data resep agar kompatibel dengan template HTML.
def prepare_meal(meal):
    """Menyiapkan format resep untuk template yang sudah ada."""
    # Menyalin dictionary agar data asli tidak termodifikasi secara tidak sengaja.
    meal = dict(meal)

    # Menetapkan nilai bawaan 'Resep tanpa nama' jika nama resep kosong.
    meal.setdefault("strMeal", "Resep tanpa nama")

    # Menetapkan nilai bawaan string kosong jika URL thumbnail tidak tersedia.
    meal.setdefault("strMealThumb", "")

    # Menetapkan nilai bawaan kategori 'Lainnya' jika kategori tidak ada.
    meal.setdefault("strCategory", "Lainnya")

    # Menetapkan nilai bawaan daerah asal 'Indonesia' jika area tidak tercatat.
    meal.setdefault("strArea", "Indonesia")

    # Mengambil dan memvalidasi daftar bahan masakan.
    ingredients = meal.get("ingredients", [])
    if not isinstance(ingredients, list):
        ingredients = []
    meal["ingredients"] = ingredients

    # Mengambil dan memvalidasi daftar tahapan instruksi memasak.
    instructions = meal.get("instructions_list", [])
    if not isinstance(instructions, list):
        instructions = []

    # Jika instructions_list kosong namun terdapat teks di strInstructions, pisahkan menjadi list baris.
    if not instructions and meal.get("strInstructions"):
        instructions = [
            step.strip()
            for step in meal["strInstructions"].splitlines()
            if step.strip()
        ]

    # Menyimpan daftar langkah yang sudah rapi ke instructions_list dan strInstructions.
    meal["instructions_list"] = instructions
    meal["strInstructions"] = "\n".join(instructions)

    # Mengembalikan objek resep yang sudah terformat rapi.
    return meal


# Mendefinisikan fungsi untuk mencari satu resep spesifik berdasarkan ID resep (meal_id).
def find_recipe(meal_id):
    """Mencari satu resep berdasarkan ID."""
    meal_id_str = str(meal_id)
    for meal in load_recipes():
        if str(meal.get("idMeal")) == meal_id_str:
            return meal
    return None


# ------------------------------------------------------------------------------
# BAGIAN 4: PENGELOLAAN MAKANAN FAVORIT (BERDASARKAN FREKUENSI DIBUKA)
# ------------------------------------------------------------------------------

# Mendefinisikan fungsi untuk membaca daftar makanan favorit yang diurutkan dari frekuensi buka terbanyak.
def get_favorites():
    """Membaca daftar makanan favorit yang diurutkan berdasarkan frekuensi dibuka pengguna."""
    if not FAVORITES_FILE.exists():
        return []

    try:
        with FAVORITES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        # Memastikan setiap data memiliki atribut view_count (minimal 1).
        for item in data:
            if isinstance(item, dict):
                item.setdefault("view_count", 1)

        # Mengurutkan daftar favorit berdasarkan view_count secara menurun (paling sering dibuka di posisi atas).
        data.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        return data

    except (OSError, json.JSONDecodeError):
        return []


# Mendefinisikan fungsi untuk menyimpan daftar makanan favorit ke berkas favorites.json.
def save_favorites(favorites):
    """Menyimpan daftar favorit ke file JSON."""
    with FAVORITES_FILE.open("w", encoding="utf-8") as file:
        json.dump(favorites, file, ensure_ascii=False, indent=2)


# Mendefinisikan fungsi untuk mencatat dan menambah frekuensi kunjungan/buka menu resep.
def record_recipe_view(meal_id):
    """Mencatat dan menambah frekuensi buka menu resep untuk menentukan makanan favorit."""
    favorites = get_favorites()
    meal_id_str = str(meal_id)
    found = False

    # Jika resep sudah pernah dibuka sebelumnya, tambahkan nilai view_count sebanyak 1.
    for item in favorites:
        if str(item.get("idMeal")) == meal_id_str:
            item["view_count"] = item.get("view_count", 0) + 1
            found = True
            break

    # Jika resep baru pertama kali dibuka, tambahkan ke favorit dengan frekuensi awal 1.
    if not found:
        meal = find_recipe(meal_id_str)
        if meal:
            favorites.append({
                "idMeal": meal.get("idMeal"),
                "strMeal": meal.get("strMeal"),
                "strMealThumb": meal.get("strMealThumb"),
                "strCategory": meal.get("strCategory"),
                "strArea": meal.get("strArea"),
                "view_count": 1
            })

    # Mengurutkan kembali seluruh daftar favorit dari view_count terbanyak.
    favorites.sort(key=lambda x: x.get("view_count", 0), reverse=True)
    save_favorites(favorites)
    return favorites


# ------------------------------------------------------------------------------
# BAGIAN 5: PENGELOLAAN FITUR SIMPAN MENU (SAVED MENUS / BOOKMARK RESEP)
# ------------------------------------------------------------------------------

# Mendefinisikan fungsi untuk membaca daftar menu yang disimpan secara manual oleh pengguna.
def get_saved_menus():
    """Membaca daftar menu yang disimpan (dibookmark) oleh pengguna dari saved_menus.json."""
    if not SAVED_MENUS_FILE.exists():
        return []

    try:
        with SAVED_MENUS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


# Mendefinisikan fungsi untuk menyimpan daftar menu yang disimpan ke berkas saved_menus.json.
def save_saved_menus(saved_menus):
    """Menyimpan daftar menu yang disimpan ke berkas saved_menus.json."""
    with SAVED_MENUS_FILE.open("w", encoding="utf-8") as file:
        json.dump(saved_menus, file, ensure_ascii=False, indent=2)


# Mendefinisikan fungsi untuk memeriksa apakah suatu resep sudah disimpan di koleksi menu.
def is_menu_saved(meal_id):
    """Memeriksa status apakah menu dengan ID tertentu sudah disimpan pengguna."""
    meal_id_str = str(meal_id)
    return any(str(item.get("idMeal")) == meal_id_str for item in get_saved_menus())


# ------------------------------------------------------------------------------
# BAGIAN 6: FLASK CONTEXT PROCESSOR (INJEKSI DATA GLOBAL KE TEMPLATE)
# ------------------------------------------------------------------------------

# Decorator context processor membuat data ini tersedia di semua file template HTML Jinja2.
@app.context_processor
def inject_global_data():
    favorites = get_favorites()
    saved_menus = get_saved_menus()

    return {
        # 'favorite_ids': Daftar ID makanan favorit (menu yang pernah dibuka).
        "favorite_ids": [
            str(item.get("idMeal"))
            for item in favorites
        ],
        # 'favorite_count': Jumlah total makanan favorit (berdasarkan frekuensi buka).
        "favorite_count": len(favorites),
        # 'favorite_view_counts': Pemetaan ID resep ke jumlah frekuensi berapa kali dibuka.
        "favorite_view_counts": {
            str(item.get("idMeal")): item.get("view_count", 1)
            for item in favorites
        },
        # 'saved_menu_count': Jumlah total resep yang disimpan secara manual oleh pengguna.
        "saved_menu_count": len(saved_menus),
        # 'saved_menu_ids': Daftar ID resep yang disimpan untuk menandai tombol 'Simpan Menu'.
        "saved_menu_ids": [
            str(item.get("idMeal"))
            for item in saved_menus
            if item.get("idMeal")
        ]
    }


# ------------------------------------------------------------------------------
# BAGIAN 7: ROUTE DAN VIEW HANDLER APLIKASI
# ------------------------------------------------------------------------------

# Route untuk halaman utama (homepage) aplikasi dengan endpoint URL root "/".
@app.route("/")
def index():
    # Memuat seluruh daftar resep lokal dari recipes.json.
    recipes = load_recipes()

    # Mengekstrak daftar kategori unik untuk tombol filter kategori.
    categories = list(dict.fromkeys(
        meal.get("strCategory", "Lainnya")
        for meal in recipes
    ))

    # Merender file template 'index.html' dengan menyuntikkan data resep unggulan dan kategori.
    return render_template(
        "index.html",
        featured=recipes[:12],
        categories=categories,
        api_available=bool(recipes)
    )


# Route untuk menangani pencarian resep dan filter berdasarkan kategori dengan URL "/search".
@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    recipes = load_recipes()
    meals = []

    # Skenario 1: Jika pengguna menyaring berdasarkan kategori tertentu.
    if category:
        meals = [
            meal for meal in recipes
            if meal.get("strCategory", "").casefold() == category.casefold()
        ]
        heading = f"Kategori: {category}"

    # Skenario 2: Jika pengguna mencari berdasarkan kata kunci teks pencarian.
    elif query:
        keyword = query.casefold()
        for meal in recipes:
            searchable_text = " ".join([
                meal.get("strMeal", ""),
                meal.get("strCategory", ""),
                meal.get("strArea", ""),
                *[
                    str(item.get("name", ""))
                    for item in meal.get("ingredients", [])
                    if isinstance(item, dict)
                ]
            ]).casefold()

            if keyword in searchable_text:
                meals.append(meal)

        heading = f'Hasil pencarian "{query}"'

    # Skenario 3: Jika pengguna mengakses halaman pencarian tanpa query.
    else:
        heading = "Cari Resep"

    # Merender template 'search.html' dengan hasil pencarian.
    return render_template(
        "search.html",
        meals=meals,
        query=query,
        category=category,
        heading=heading
    )


# Route untuk menampilkan halaman detail dari suatu resep berdasarkan ID resep dinamis.
@app.route("/recipe/<meal_id>")
def recipe_detail(meal_id):
    meal = find_recipe(meal_id)

    # Validasi jika resep tidak ditemukan di koleksi.
    if meal is None:
        flash("Resep tidak ditemukan dalam koleksi lokal.", "error")
        return redirect(url_for("index"))

    # Menambah frekuensi buka menu resep ini secara otomatis (mengupdate peringkat makanan favorit).
    record_recipe_view(meal_id)

    # Mengambil nilai frekuensi buka terkini dari resep ini.
    favorites = get_favorites()
    view_count = next(
        (
            item.get("view_count", 1)
            for item in favorites
            if str(item.get("idMeal")) == str(meal_id)
        ),
        1
    )

    # Memeriksa apakah resep ini saat ini tersimpan di koleksi menu tersimpan pengguna.
    is_saved = is_menu_saved(meal_id)

    # Merender template 'detail.html' dengan menyertakan data resep, frekuensi buka, dan status simpan.
    return render_template(
        "detail.html",
        meal=meal,
        view_count=view_count,
        is_saved=is_saved
    )


# Route untuk fitur "Surprise Me" yang memilih dan mengalihkan pengguna ke resep acak.
@app.route("/random")
def random_recipe():
    recipes = load_recipes()
    if recipes:
        meal = random.choice(recipes)
        return redirect(url_for("recipe_detail", meal_id=meal["idMeal"]))

    flash("Koleksi resep masih kosong atau tidak bisa dibaca.", "error")
    return redirect(url_for("index"))


# ------------------------------------------------------------------------------
# BAGIAN 8: ROUTE MAKANAN FAVORIT (BERDASARKAN FREKUENSI DIBUKA)
# ------------------------------------------------------------------------------

# Route untuk menampilkan seluruh daftar makanan favorit yang diurutkan dari frekuensi buka terbanyak.
@app.route("/favorites")
def favorites():
    saved_favs = get_favorites()
    local_recipes = {
        str(meal["idMeal"]): meal
        for meal in load_recipes()
    }

    # Menggabungkan data resep lokal lengkap dengan data view_count yang tersimpan.
    meals = []
    for item in saved_favs:
        meal_id_str = str(item.get("idMeal"))
        meal_data = dict(local_recipes.get(meal_id_str, item))
        meal_data["view_count"] = item.get("view_count", 1)
        meals.append(meal_data)

    # Merender template 'favorites.html' dengan daftar menu terurut dari yang paling sering dibuka.
    return render_template("favorites.html", meals=meals)


# Route POST untuk menghapus atau mereset resep dari daftar makanan favorit.
@app.route("/favorites/toggle/<meal_id>", methods=["POST"])
def toggle_favorite(meal_id):
    favorites_list = get_favorites()
    meal_id_str = str(meal_id)

    existing = next(
        (item for item in favorites_list if str(item.get("idMeal")) == meal_id_str),
        None
    )

    if existing:
        favorites_list = [item for item in favorites_list if str(item.get("idMeal")) != meal_id_str]
        save_favorites(favorites_list)
        flash("Resep dihapus dari daftar makanan favorit.", "success")
    else:
        meal = find_recipe(meal_id_str)
        if meal is None:
            flash("Resep tidak ditemukan.", "error")
            return redirect(request.referrer or url_for("index"))

        favorites_list.append({
            "idMeal": meal.get("idMeal"),
            "strMeal": meal.get("strMeal"),
            "strMealThumb": meal.get("strMealThumb"),
            "strCategory": meal.get("strCategory"),
            "strArea": meal.get("strArea"),
            "view_count": 1
        })
        favorites_list.sort(key=lambda x: x.get("view_count", 0), reverse=True)
        save_favorites(favorites_list)
        flash("Resep ditambahkan ke daftar makanan favorit!", "success")

    return redirect(request.referrer or url_for("index"))


# ------------------------------------------------------------------------------
# BAGIAN 9: ROUTE FITUR SIMPAN MENU (SAVED MENUS / TEMPAT SIMPAN MENU)
# ------------------------------------------------------------------------------

# Route untuk menampilkan halaman koleksi Menu yang Disimpan oleh pengguna.
@app.route("/saved-menus")
def saved_menus():
    query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()

    all_saved = get_saved_menus()
    local_recipes = {str(m["idMeal"]): m for m in load_recipes()}

    # Mengumpulkan daftar kategori unik dari menu yang disimpan untuk filter dropdown.
    categories = sorted(list(dict.fromkeys(
        item.get("strCategory", "Lainnya")
        for item in all_saved
        if item.get("strCategory")
    )))

    # Menyaring berdasarkan kategori jika dipilih pengguna.
    filtered_menus = all_saved
    if selected_category:
        filtered_menus = [
            m for m in filtered_menus
            if m.get("strCategory", "").casefold() == selected_category.casefold()
        ]

    # Menyaring berdasarkan kata kunci pencarian jika diketik pengguna.
    if query:
        q_lower = query.casefold()
        filtered_menus = [
            m for m in filtered_menus
            if q_lower in str(m.get("strMeal", "")).casefold()
            or q_lower in str(m.get("strCategory", "")).casefold()
            or q_lower in str(m.get("strArea", "")).casefold()
            or q_lower in str(m.get("notes", "")).casefold()
        ]

    # Memperbarui informasi resep dengan data terbaru dari local_recipes jika ada.
    enriched_menus = []
    for item in filtered_menus:
        meal_id_str = str(item.get("idMeal"))
        recipe_data = local_recipes.get(meal_id_str, {})
        merged_item = dict(item)
        if recipe_data:
            merged_item.setdefault("strMeal", recipe_data.get("strMeal"))
            merged_item.setdefault("strMealThumb", recipe_data.get("strMealThumb"))
            merged_item.setdefault("strCategory", recipe_data.get("strCategory"))
            merged_item.setdefault("strArea", recipe_data.get("strArea"))
        enriched_menus.append(merged_item)

    # Merender template antarmuka 'saved_menus.html'.
    return render_template(
        "saved_menus.html",
        saved_menus=enriched_menus,
        total_count=len(all_saved),
        categories=categories,
        query=query,
        selected_category=selected_category
    )


# Route dengan metode POST untuk menambah atau menghapus menu dari daftar Menu yang Disimpan (toggle).
@app.route("/saved-menus/toggle/<meal_id>", methods=["POST"])
def toggle_save_menu(meal_id):
    saved_list = get_saved_menus()
    meal_id_str = str(meal_id)

    # Mencari apakah resep sudah ada di dalam daftar menu yang disimpan.
    existing = next(
        (item for item in saved_list if str(item.get("idMeal")) == meal_id_str),
        None
    )

    # Skenario A: Jika SUDAH DISIMPAN, maka hapus dari simpanan (unbookmark).
    if existing:
        saved_list = [item for item in saved_list if str(item.get("idMeal")) != meal_id_str]
        save_saved_menus(saved_list)
        flash(f'Menu "{existing.get("strMeal", "Resep")}" dihapus dari Menu yang Disimpan.', "success")

    # Skenario B: Jika BELUM DISIMPAN, maka tambahkan ke daftar simpanan.
    else:
        meal = find_recipe(meal_id_str)
        if meal is None:
            flash("Menu resep tidak ditemukan.", "error")
            return redirect(request.referrer or url_for("saved_menus"))

        # Mengambil catatan opsional jika dikirim via formulir.
        notes = request.form.get("notes", "").strip()

        # Menyimpan ringkasan menu beserta stempel waktu penyimpanan.
        saved_list.insert(0, {
            "idMeal": meal.get("idMeal"),
            "strMeal": meal.get("strMeal"),
            "strMealThumb": meal.get("strMealThumb"),
            "strCategory": meal.get("strCategory"),
            "strArea": meal.get("strArea"),
            "saved_at": datetime.now().strftime("%d %b %Y, %H:%M WIB"),
            "notes": notes
        })
        save_saved_menus(saved_list)
        flash(f'Menu "{meal.get("strMeal")}" berhasil disimpan ke Menu yang Disimpan!', "success")

    # Mengembalikan pengguna ke halaman pemanggil (referrer) atau fallback ke saved_menus.
    return redirect(request.referrer or url_for("saved_menus"))


# Route dengan metode POST untuk memperbarui catatan pribadi pada menu yang disimpan.
@app.route("/saved-menus/note/<meal_id>", methods=["POST"])
def update_menu_note(meal_id):
    saved_list = get_saved_menus()
    meal_id_str = str(meal_id)
    notes = request.form.get("notes", "").strip()

    # Memperbarui catatan pada item menu yang cocok.
    for item in saved_list:
        if str(item.get("idMeal")) == meal_id_str:
            item["notes"] = notes
            break

    save_saved_menus(saved_list)
    flash("Catatan resep berhasil disimpan!", "success")
    return redirect(request.referrer or url_for("saved_menus"))


# Route dengan metode POST untuk menghapus menu dari daftar simpanan secara langsung.
@app.route("/saved-menus/delete/<meal_id>", methods=["POST"])
def delete_saved_menu(meal_id):
    saved_list = get_saved_menus()
    meal_id_str = str(meal_id)

    target = next((item for item in saved_list if str(item.get("idMeal")) == meal_id_str), None)
    saved_list = [item for item in saved_list if str(item.get("idMeal")) != meal_id_str]
    save_saved_menus(saved_list)

    name = target.get("strMeal", "Menu") if target else "Menu"
    flash(f'Menu "{name}" berhasil dihapus dari Menu yang Disimpan.', "success")
    return redirect(request.referrer or url_for("saved_menus"))


# Route untuk menampilkan halaman statis "Tentang Aplikasi" (About Page).
@app.route("/about")
def about():
    return render_template("about.html")


# ------------------------------------------------------------------------------
# BAGIAN 10: BLOK EKSEKUSI UTAMA (ENTRY POINT APLIKASI)
# ------------------------------------------------------------------------------

# Fungsi pembantu untuk mendeteksi alamat IP lokal (LAN / Wi-Fi) komputer secara dinamis.
def get_local_ip():
    """Mendapatkan alamat IP lokal komputer agar website dapat diakses dari perangkat lain (HP)."""
    try:
        # Membuat koneksi socket dummy UDP ke DNS publik untuk mendeteksi adapter jaringan aktif.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        # Mendapatkan alamat IP lokal komputer dari adapter jaringan yang sedang aktif.
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        # Fallback ke 127.0.0.1 jika komputer tidak terhubung ke jaringan Wi-Fi/LAN.
        return "127.0.0.1"


# Memastikan server Flask hanya dijalankan saat berkas ini dieksekusi secara langsung.
if __name__ == "__main__":
    # Mengambil alamat IP lokal komputer secara otomatis.
    host_ip = get_local_ip()
    # Menetapkan nomor port aplikasi web (standar port 5000).
    server_port = 5000

    # Mencetak petunjuk tautan akses yang jelas ke terminal untuk kemudahan pengguna.
    print("\n" + "=" * 65)
    print("🚀 SERVER FOOD RECIPE FINDER SIAP DIGUNAKAN!")
    print("=" * 65)
    print(f"📱 Tautan Akses di HP (Pastikan 1 Wi-Fi) : http://{host_ip}:{server_port}")
    print(f"💻 Tautan Akses di Komputer / Laptop ini : http://localhost:{server_port}")
    print(f"                                        : http://127.0.0.1:{server_port}")
    print("=" * 65 + "\n")

    # Menjalankan server Flask dengan host='0.0.0.0' agar terbuka untuk koneksi dari HP di jaringan yang sama.
    app.run(host="0.0.0.0", port=server_port, debug=True)
