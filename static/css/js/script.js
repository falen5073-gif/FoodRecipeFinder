// ==============================================================================
// SKRIP INTERAKSI CLIENT-SIDE JAVASCRIPT (static/css/js/script.js)
// ==============================================================================
// Berkas ini mengatur fungsionalitas interaktif pada sisi browser (klien),
// khususnya fitur toggle tema tampilan (Dark Mode / Light Mode) dan
// persistensi preferensi tema pengguna menggunakan Web Storage (localStorage).
// ==============================================================================

// Mengambil elemen tombol pengubah tema dari dokumen HTML berdasarkan ID 'themeToggle'.
const themeToggle = document.getElementById("themeToggle");

// Membaca preferensi tema yang sebelumnya disimpan di browser melalui localStorage dengan kunci 'foodie-theme'.
const savedTheme = localStorage.getItem("foodie-theme");

// Memeriksa jika tema yang tersimpan sebelumnya adalah mode gelap ("dark").
if (savedTheme === "dark") {
    // Menambahkan class 'dark-mode' pada elemen <body> agar gaya CSS mode gelap diterapkan.
    document.body.classList.add("dark-mode");
}

// Mendefinisikan fungsi untuk memperbarui tampilan ikon dan atribut aksesibilitas tombol tema.
function updateThemeButton() {
    // Jika elemen tombol themeToggle tidak ditemukan di halaman, hentikan eksekusi fungsi (guard clause).
    if (!themeToggle) return;

    // Memeriksa apakah saat ini body memiliki class 'dark-mode' (menghasilkan boolean true/false).
    const isDark = document.body.classList.contains("dark-mode");

    // Mengubah simbol/ikon tombol: '☀' (matahari) jika sedang mode gelap, atau '☾' (bulan) jika mode terang.
    themeToggle.textContent = isDark ? "☀" : "☾";

    // Memperbarui atribut aria-label untuk pembaca layar (screen reader) demi aksesibilitas web.
    themeToggle.setAttribute(
        "aria-label",
        isDark ? "Aktifkan mode terang" : "Aktifkan mode gelap"
    );
}

// Memanggil fungsi updateThemeButton saat pertama kali skrip dimuat agar tampilan tombol sesuai tema awal.
updateThemeButton();

// Memastikan bahwa elemen tombol themeToggle tersedia sebelum menambahkan event listener.
if (themeToggle) {
    // Menambahkan event listener untuk menangani aksi klik pengguna pada tombol tema.
    themeToggle.addEventListener("click", () => {
        // Melakukan toggle (menambah jika belum ada, menghapus jika sudah ada) class 'dark-mode' pada body.
        document.body.classList.toggle("dark-mode");

        // Menentukan status tema saat ini ('dark' jika memiliki class 'dark-mode', selain itu 'light').
        const theme = document.body.classList.contains("dark-mode")
            ? "dark"
            : "light";

        // Menyimpan preferensi tema terbaru ke localStorage browser agar tidak hilang saat halaman direfresh.
        localStorage.setItem("foodie-theme", theme);

        // Memperbarui tampilan ikon tombol tema agar sinkron dengan status tema yang baru.
        updateThemeButton();
    });
}
