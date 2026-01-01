import os
import sys
import requests
import zipfile
import json
from bs4 import BeautifulSoup
import re

def download_chrome_extension(extension_id, version='latest'):
    """
    Download extension langsung dari Chrome Web Store
    """
    # URL dasar Chrome Web Store
    details_url = f'https://chrome.google.com/webstore/detail/{extension_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://chrome.google.com/webstore'
    }
    
    if version == 'latest':
        # Dapatkan versi terbaru dari halaman detail
        print(f'Mengambil informasi extension dari: {details_url}')
        response = requests.get(details_url, headers=headers)
        
        # Parse versi dari halaman
        version = '1.0.0'  # Default
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    # Coba beberapa pola untuk mendapatkan versi
                    patterns = [
                        r'"latestVersion":"([\d.]+)"',
                        r'"version":"([\d.]+)"',
                        r'version["\s:]+([\d.]+)',
                        r'Version["\s:]+([\d.]+)'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, script.string)
                        if match:
                            version = match.group(1)
                            print(f'Versi ditemukan: {version}')
                            break
                    if version != '1.0.0':
                        break
    
    print(f'\nMencoba download: {extension_id} v{version}')
    
    # Coba beberapa format URL download
    download_urls = [
        # Format 1: Standard dengan prodversion terbaru
        f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=131.0&x=id%3D{extension_id}%26installsource%3Dondemand%26uc',
        # Format 2: Tanpa parameter uc
        f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=131.0&x=id%3D{extension_id}%26installsource%3Dondemand',
        # Format 3: Format alternatif
        f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=120.0&x=id%3D{extension_id}%26installsource%3Dondemand%26uc',
        # Format 4: Format lama
        f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=109.0&x=id%3D{extension_id}%26installsource%3Dondemand%26uc',
        # Format 5: Format dengan acceptformat
        f'https://clients2.google.com/service/update2/crx?response=redirect&prodversion=131.0&acceptformat=crx2,crx3&x=id%3D{extension_id}%26installsource%3Dondemand%26uc'
    ]
    
    download_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': details_url,
        'Origin': 'https://chrome.google.com'
    }
    
    # Coba setiap URL sampai berhasil
    for i, download_url in enumerate(download_urls, 1):
        print(f'\nMencoba metode {i}/{len(download_urls)}...')
        print(f'URL: {download_url[:80]}...')
        
        # Download file dengan headers
        response = requests.get(download_url, headers=download_headers, stream=True, allow_redirects=True, timeout=30)
        
        # Periksa status code
        if response.status_code == 200 and len(response.content) > 0:
            print(f'[SUKSES] Download berhasil!')
            filename = f'{extension_id}_v{version}.crx'
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f'Downloaded: {filename}')
            
            # Convert .crx to .zip (CRX adalah ZIP dengan header khusus)
            with open(filename, 'rb') as crx_file:
                crx_data = crx_file.read()
            
            # Lewati header CRX (16-21 bytes magic number + version)
            zip_start = 0
            if crx_data[0:4] == b'Cr24':  # CRX3 format
                # Parse CRX3 header
                import struct
                # Magic number (4) + version (4) + header length (4)
                header_size = struct.unpack('<I', crx_data[8:12])[0]
                zip_start = 12 + header_size
            elif crx_data[0:2] == b'Cr':  # CRX2 format
                zip_start = 16
            
            # Extract ZIP
            zip_filename = f'{extension_id}_v{version}.zip'
            with open(zip_filename, 'wb') as zip_file:
                zip_file.write(crx_data[zip_start:])
            
            # Extract contents
            extract_dir = f'{extension_id}_source'
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print(f'[SUKSES] Extracted to: {extract_dir}/')
            
            # Cleanup
            os.remove(filename)
            os.remove(zip_filename)
            
            return extract_dir
        elif response.status_code == 200 and len(response.content) == 0:
            print(f'  Status 200 tapi konten kosong, mencoba metode berikutnya...')
            continue
        elif response.status_code == 204:
            print(f'  Status 204 (No Content), mencoba metode berikutnya...')
            continue
        elif response.status_code == 302 or response.status_code == 301:
            # Redirect, coba ikuti redirect
            redirect_url = response.headers.get('Location', '')
            print(f'  Redirect ke: {redirect_url[:80] if redirect_url else "N/A"}...')
            if redirect_url:
                redirect_response = requests.get(redirect_url, headers=download_headers, stream=True, allow_redirects=True, timeout=30)
                if redirect_response.status_code == 200 and len(redirect_response.content) > 0:
                    # Gunakan redirect_response untuk proses download
                    print(f'[SUKSES] Download berhasil dari redirect!')
                    filename = f'{extension_id}_v{version}.crx'
                    with open(filename, 'wb') as f:
                        for chunk in redirect_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f'Downloaded: {filename}')
                    
                    # Convert .crx to .zip (CRX adalah ZIP dengan header khusus)
                    with open(filename, 'rb') as crx_file:
                        crx_data = crx_file.read()
                    
                    # Lewati header CRX (16-21 bytes magic number + version)
                    zip_start = 0
                    if crx_data[0:4] == b'Cr24':  # CRX3 format
                        import struct
                        header_size = struct.unpack('<I', crx_data[8:12])[0]
                        zip_start = 12 + header_size
                    elif crx_data[0:2] == b'Cr':  # CRX2 format
                        zip_start = 16
                    
                    # Extract ZIP
                    zip_filename = f'{extension_id}_v{version}.zip'
                    with open(zip_filename, 'wb') as zip_file:
                        zip_file.write(crx_data[zip_start:])
                    
                    # Extract contents
                    extract_dir = f'{extension_id}_source'
                    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    print(f'[SUKSES] Extracted to: {extract_dir}/')
                    
                    # Cleanup
                    os.remove(filename)
                    os.remove(zip_filename)
                    
                    return extract_dir
            continue
        else:
            print(f'  Status code {response.status_code}, mencoba metode berikutnya...')
            continue
    
    # Jika semua metode gagal
    print('\n[GAGAL] Semua metode download gagal!')
    print('\nKemungkinan penyebab:')
    print('1. Chrome Web Store telah mengubah kebijakan download')
    print('2. Extension memerlukan autentikasi untuk download')
    print('3. Extension tidak tersedia untuk download langsung')
    print('\n[INFO] Alternatif:')
    print('- Gunakan Chrome Extension Downloader online (crxextractor.com, etc)')
    print('- Install extension langsung dari Chrome Web Store, lalu ekstrak dari folder Chrome')
    print('- Gunakan Chrome dengan Developer Mode untuk load unpacked extension')
    return None

# Contoh penggunaan
if __name__ == '__main__':
    # ID ekstensi (dapat dari URL Chrome Web Store)
    # Contoh: https://chrome.google.com/webstore/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm
    # ID: cjpalhdlnbpafiamejdnhcphjbkeiagm
    
    if len(sys.argv) > 1:
        # Ambil Extension ID dari command line argument
        extension_id = sys.argv[1].strip()
    else:
        # Atau minta input dari user
        extension_id = input('Enter Extension ID: ').strip()
    
    if extension_id:
        download_chrome_extension(extension_id)
    else:
        print('Error: Extension ID tidak boleh kosong!')
        print('Usage: python download_extension.py <extension_id>')
        print('Contoh: python download_extension.py cjpalhdlnbpafiamejdnhcphjbkeiagm')