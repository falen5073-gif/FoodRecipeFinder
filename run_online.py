# ==============================================================================
# SKRIP RUNNER ONLINE (run_online.py)
# ==============================================================================
# Skrip ini menjalankan aplikasi Food Recipe Finder agar bisa diakses dari HP
# atau perangkat lain dari mana saja melalui internet tanpa harus berada
# di jaringan Wi-Fi yang sama (menggunakan teknologi Cloudflare Tunnel gratis).
# ==============================================================================

# Library bawaan Python untuk interaksi sistem dan berkas
import os

# Library bawaan Python untuk pencarian pola ekspresi reguler (regex) URL
import re

# Library bawaan Python untuk mengakses argumen dan konfigurasi interpreter
import sys

# Library bawaan Python untuk jeda waktu dan penghitungan timeout
import time

# Library bawaan Python untuk menemukan path berkas executable sistem (seperti npx.cmd)
import shutil

# Library bawaan Python untuk menjalankan proses latar belakang (subprocess)
import subprocess

# Menentukan port lokal yang digunakan oleh aplikasi Flask
PORT = 5000

# Menentukan path interpreter Python saat ini
PYTHON_EXE = sys.executable


# Fungsi untuk menjalankan server web Flask lokal
def start_flask():
    """Menjalankan server web Flask lokal sebagai background process."""
    return subprocess.Popen(
        [PYTHON_EXE, "app.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# Fungsi untuk menjalankan Cloudflare Tunnel
def start_tunnel():
    """Menjalankan Cloudflare Tunnel untuk mengekspos localhost ke internet publik."""
    # Mendapatkan path lengkap executable npx di sistem Windows (npx.cmd)
    npx_bin = shutil.which("npx") or "npx.cmd"
    cmd = [npx_bin, "--yes", "cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )


# Fungsi utama yang mengatur alur eksekusi online
def main():
    print("=" * 70, flush=True)
    print("⏳ SEDANG MEMULAI SERVER & MEMBUAT LINK AKSES PUBLIK (INTERNET)...", flush=True)
    print("=" * 70, flush=True)

    # 1. Jalankan server Flask lokal
    flask_process = start_flask()
    time.sleep(2)  # Memberi jeda 2 detik agar Flask siap menerima koneksi

    # 2. Jalankan Cloudflare Tunnel
    tunnel_process = start_tunnel()

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # 3. Baca output tunnel untuk menangkap tautan publik
    try:
        start_time = time.time()
        for line in iter(tunnel_process.stdout.readline, ""):
            match = url_pattern.search(line)
            if match:
                public_url = match.group(0)
                break
            # Batas waktu tunggu maksimal 35 detik
            if time.time() - start_time > 35:
                break

        if public_url:
            print("\n" + "=" * 70, flush=True)
            print("🎉 WEBSITE BERHASIL TERHUBUNG KE INTERNET PUBLIK!", flush=True)
            print("=" * 70, flush=True)
            print("📱 BUKA DI HP (Bisa pakai Kuota Data 4G/5G atau Wi-Fi MANA SAJA):", flush=True)
            print(f"   👉 {public_url}", flush=True)
            print("\n💻 BUKA DI KOMPUTER / LAPTOP INI:", flush=True)
            print(f"   👉 http://localhost:{PORT}", flush=True)
            print("=" * 70, flush=True)
            print("ℹ️  Petunjuk Penggunaan:", flush=True)
            print("   1. Salin dan buka link di atas pada browser HP Anda (Chrome, Safari, dll).", flush=True)
            print("   2. Link ini dapat diakses dari mana saja tanpa perlu satu Wi-Fi.", flush=True)
            print("   3. Jangan tutup jendela terminal ini selama Anda membuka web di HP.", flush=True)
            print("   4. Tekan Ctrl+C untuk mematikan server.", flush=True)
            print("=" * 70 + "\n", flush=True)

            # Menjaga proses tetap hidup
            while True:
                time.sleep(1)

        else:
            print("\n❌ Gagal mendapatkan tautan publik otomatis dalam 35 detik.", flush=True)
            print("   Pastikan komputer Anda terhubung ke internet.", flush=True)

    except KeyboardInterrupt:
        print("\n🛑 Menghentikan server dan tunnel...", flush=True)

    finally:
        # Membersihkan proses saat keluar
        try:
            tunnel_process.terminate()
            flask_process.terminate()
        except Exception:
            pass
        print("✅ Server telah dimatikan dengan aman.", flush=True)


# Entry point eksekusi skrip
if __name__ == "__main__":
    main()
