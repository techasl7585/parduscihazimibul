# Pardus Cihazımı Bul

Pardus Cihazımı Bul, açık ve internete bağlı bir Pardus bilgisayarın son
konumunu telefonda gösteren, tek düğmeli açık kaynaklı bir masaüstü
uygulamasıdır.

## İlk sürüm

- Pardus tarafı tarayıcıda değil, yerel GTK masaüstü uygulamasında çalışır.
- Kullanıcı tek bir **Konumumu Paylaş** düğmesine basar.
- Konum paylaşımı kurulumdan sonra varsayılan olarak kapalıdır.
- Kullanıcı paylaşımı durdurduğunda cihaz kaydı panelden kaldırılır.
- Arka plan servisi sistem açılışında otomatik başlar.
- Konumu Pardus Konum Servisi (GeoClue) üzerinden otomatik alır.
- GeoClue; bilgisayardaki Wi-Fi, modem GPS, ağ GPS'i ve desteklenen diğer
  konum kaynaklarından uygun olanı kullanır.
- GPS olmayan bilgisayarlarda GeoClue sonuç vermezse uygulama bilgisayarın
  gördüğü Wi-Fi ağlarını Positon ile konumlandırır.
- Positon da sonuç üretemezse BeaconDB Wi-Fi/ağ konumu son yedek olarak
  kullanılır; ayrı ve ücretli bir proje sunucusu gerekmez.
- Konum telefondan değil, her zaman Pardus bilgisayarın kendi konum
  kaynaklarından alınır.
- Cihaz her 15 saniyede merkeze çevrim içi sinyali gönderir.
- Telefon web panelinde çevrim içi/çevrim dışı durumu gösterilir.
- Son görülme zamanı, yerel IP ve konum kaynağı gösterilir.
- Konum OpenStreetMap üzerinde işaretlenir.
- Telefon haritası paket içindeki Leaflet 1.9.4 ile etkileşimli çalışır.
- Telefon erişimi 8 haneli kodla korunur.

## Desteklenen sistem

- Pardus 25 güncel masaüstü sürümü
- x86_64/amd64 bilgisayar
- İnternet bağlantısı

Uygulama Node.js, npm veya Flutter kullanmaz. Gerekli GeoClue ve Python
bağlantıları `.deb` bağımlılığıdır; `apt install ./paket.deb` komutu bunları
Pardus deposundan otomatik kurar.

## Kurulum

GitHub deposundaki hazır `.deb` kurulum paketini indirin:

[Pardus Cihazımı Bul 0.1.7 paketini indir](https://github.com/techasl7585/parduscihazimibul/raw/main/pardus-cihazimi-bul_0.1.7_amd64.deb)

```bash
sudo apt install ./pardus-cihazimi-bul_0.1.7_amd64.deb
```

Kurulum bittiğinde uygulamalar menüsünden **Pardus Cihazımı Bul** seçeneğini
açın ve **Konumumu Paylaş** düğmesine basın. Arka plan servisi kurulum sırasında
etkinleştirilir.

## Web paneliyle deneme

1. Bilgisayarda Pardus Cihazımı Bul uygulamasını açın.
2. **Konumumu Paylaş** düğmesine basın.
3. Telefonu veya diğer cihazı bilgisayarla aynı Wi-Fi ağına bağlayın.
4. Uygulamadaki web paneli adresini açıp 8 haneli kodu girin.
5. Bilgisayarın konumu uygulama görünümlü mobil panelde açılır.

Bu ilk yerel prototipte telefon ve merkez bilgisayar aynı ağda olmalıdır.
Farklı ağlardan kullanım için merkez servisi internetteki HTTPS sunucuya
kurulur ve Pardus ajanında yalnızca **Merkez web adresi** değiştirilir. Sunucu
yayını ilk sürüme dahil değildir.

## Konum doğruluğu

Konum kaynağı Pardus Konum Servisi'dir. Bilgisayarda GPS donanımı varsa
GeoClue GPS'i; yoksa Wi-Fi, modem veya ağ tabanlı konum kaynağını kullanabilir.
Paket önce GeoClue'yu kullanır. GeoClue sonuç üretmezse uygulama
NetworkManager'dan bilgisayarın gördüğü Wi-Fi erişim noktalarını alıp
`https://api.positon.xyz/v1/geolocate` adresine sorgular. Positon sonucu
alınamazsa `https://api.beacondb.net/v1/geolocate` son yedek olarak kullanılır.
BeaconDB kapsaması bulunmazsa daha yaklaşık bir ağ/IP sonucu dönebilir. Hiçbir
yöntem sonuç üretmezse uygulama konum kaynağının bulunamadığını açıkça gösterir.

Sürüm 0.1.7, yarışma prototipinde Positon'ın çok düşük kullanım limitli `test`
anahtarını kullanır. Dağıtıma çıkarken açık kaynak projeler için Positon'dan
`admin@positon.xyz` adresi üzerinden proje anahtarı istenmeli ve aşağıdaki
komutlarla kurulmalıdır:

```bash
printf '%s\n' 'ALINAN_ANAHTAR' | \
  sudo tee /etc/pardus-cihazimi-bul/positon-api-key >/dev/null
sudo chown root:pardus-find /etc/pardus-cihazimi-bul/positon-api-key
sudo chmod 0640 /etc/pardus-cihazimi-bul/positon-api-key
sudo systemctl restart pardus-cihazimi-bul.service
```

## Geliştirici çalıştırması

```bash
chmod +x run-dev.sh
./run-dev.sh
```

Panel `http://127.0.0.1:8765` adresinde açılır.

## Paket oluşturma

Pardus/Debian sistemde:

```bash
chmod +x build-deb.sh
./build-deb.sh
```

Paket `build/` klasörüne yazılır.

## Güvenlik ve gizlilik

- Konum paylaşımı panelden kapatılabilir.
- Ayarlar yalnızca bilgisayarın kendisinden değiştirilebilir.
- Telefon paneli erişim kodu ister.
- Kurum anahtarı olmayan cihazlar merkeze veri gönderemez.
- Uygulama servisi ayrı ve yetkisiz bir sistem kullanıcısıyla çalışır.
- Konum paylaşımı açıldığında GeoClue sonuç vermezse uygulama, bilgisayarın
  yakındaki Wi-Fi erişim noktalarının BSSID ve sinyal bilgilerini konum
  hesaplaması için önce Positon'a, gerekirse BeaconDB'ye sorgular.
- Gizli SSID'ler ve adı `_nomap` ile biten ağlar bu sorguya dahil edilmez.
- BeaconDB'ye yeni GPS/Wi-Fi verisi katkısı `submit-data=false` ile kapalıdır.
- İnternete yayınlanacak merkez mutlaka HTTPS arkasında çalıştırılmalıdır.

## Kullanılan açık veriler

Harita OpenStreetMap verilerini kullanır. Konum öncelikle Pardus Konum
Servisi'nden alınır; sonuç alınamazsa Positon Wi-Fi konumu, ardından BeaconDB
Wi-Fi/ağ konumu yedek olarak kullanılır. Leaflet 1.9.4, BSD-2-Clause
lisansıyla paket içinde dağıtılır.
