# Pardus Cihazımı Bul

Pardus Cihazımı Bul, açık durumdaki bir Pardus bilgisayarın konumunu tek
düğmeyle paylaşan ve aynı ağdaki telefon, tablet veya başka bir bilgisayardan
web paneli üzerinden görüntüleyen açık kaynaklı bir cihaz konum uygulamasıdır.

> Güncel sürüm: **0.1.7**  
> Bu sürüm, aynı Wi-Fi ağı içinde çalışan yerel prototiptir.

## İndir ve kur

### Grafik arayüzle kurulum

1. [Pardus Cihazımı Bul 0.1.7 `.deb` paketini indirin.](https://github.com/techasl7585/parduscihazimibul/raw/main/pardus-cihazimi-bul_0.1.7_amd64.deb)
2. İndirilen pakete çift tıklayın.
3. Pardus Paket Kurucu'da **Kur** düğmesine basın.
4. İstendiğinde sistem parolanızı girin.
5. Uygulamalar menüsünden **Pardus Cihazımı Bul** uygulamasını açın.

Terminal kullanmak zorunlu değildir. Kurulum paketi gerekli Python, GTK,
GeoClue ve ağ bileşenlerini Pardus depolarından otomatik olarak kurar; arka plan
servisini oluşturur ve sistem başlangıcında etkinleştirir.

İlk kurulum sırasında bağımlılıkların indirilebilmesi için internet bağlantısı
gerekir.

### Terminalle alternatif kurulum

```bash
sudo apt install ./pardus-cihazimi-bul_0.1.7_amd64.deb
```

## Ne işe yarar?

- Kullanıcı **Konumumu Paylaş** düğmesine basarak paylaşımı başlatır.
- Bilgisayar kendi konumunu kendi konum kaynaklarıyla belirler.
- Uygulama, aynı Wi-Fi ağından erişilebilen web paneli adresini gösterir.
- Web paneli telefon, tablet ve bilgisayar tarayıcılarında çalışır.
- Bilgisayarın konumu OpenStreetMap üzerinde işaretlenir.
- Cihazın çevrim içi durumu, son görülme zamanı, yerel IP adresi ve konum
  doğruluğu gösterilir.
- Web paneli 8 haneli erişim koduyla korunur.
- Kullanıcı paylaşımı durdurduğunda cihaz kaydı web panelinden kaldırılır.

## Nasıl çalışır?

```mermaid
flowchart LR
    A["Konumumu Paylaş"] --> B["Pardus konum kaynakları"]
    B --> C["Yerel arka plan servisi"]
    C --> D["Aynı ağdaki web paneli"]
```

Uygulama konumu aşağıdaki sırayla arar:

1. **Pardus Konum Servisi (GeoClue):** GPS, modem ve desteklenen sistem konum
   kaynaklarını kullanır.
2. **Positon Wi-Fi konumu:** GeoClue sonuç vermezse bilgisayarın çevresinde
   gördüğü Wi-Fi erişim noktalarından konum hesaplar.
3. **BeaconDB:** Diğer kaynaklar sonuç üretmezse son yedek konum kaynağı olarak
   kullanılır.

Konum telefondan alınmaz. Telefon veya diğer cihaz yalnızca Pardus
bilgisayarın paylaştığı konumu web panelinde görüntüler.

## Kullanım

1. Pardus bilgisayarda uygulamayı açın.
2. **Konumumu Paylaş** düğmesine basın.
3. Ekranda gösterilen web paneli adresini kopyalayın.
4. Görüntüleme yapacağınız cihazı aynı Wi-Fi ağına bağlayın.
5. Adresi cihazın web tarayıcısında açın.
6. Uygulamada gösterilen 8 haneli erişim kodunu girin.

Paylaşımı kapatmak için Pardus uygulamasındaki **Paylaşımı Durdur** düğmesine
basın.

## Sistem gereksinimleri

| Gereksinim | Destek |
|---|---|
| İşletim sistemi | Pardus 25 masaüstü |
| İşlemci mimarisi | x86_64 / amd64 |
| Ağ | Bilgisayar ve görüntüleyen cihaz aynı Wi-Fi ağında |
| İnternet | Kurulum, konum servisleri ve harita için gerekli |
| GPS | Zorunlu değil |
| Node.js / npm / Flutter | Gerekli değil |

## Konum doğruluğu

Konum doğruluğu bilgisayardaki donanıma, çevrede görülen Wi-Fi ağı sayısına ve
konum sağlayıcılarının kapsamasına göre değişir.

| Kaynak | Beklenen davranış |
|---|---|
| GeoClue ve GPS | Donanım destekliyorsa en hassas sonuç |
| Positon Wi-Fi | Yakındaki Wi-Fi veritabanı kapsamasına göre yaklaşık sonuç |
| BeaconDB | Son yedek; bazı bölgelerde şehir veya ağ seviyesinde sonuç |

Geliştirme testinde 28 Wi-Fi erişim noktasıyla Positon yaklaşık **124 metre**
doğruluk bildirmiştir. Bu değer tüm cihaz ve bölgeler için garanti değildir.

## Güvenlik ve gizlilik

- Konum paylaşımı kurulumdan sonra varsayılan olarak kapalıdır.
- Konum yalnızca kullanıcı paylaşımı açtığında alınır.
- Ayarlar yalnızca Pardus bilgisayarın kendisinden değiştirilebilir.
- Web paneli 8 haneli erişim koduyla korunur.
- Arka plan servisi ayrı ve yetkisiz `pardus-find` sistem kullanıcısıyla
  çalışır.
- GeoClue sonuç vermezse yalnızca Wi-Fi erişim noktalarının BSSID ve sinyal
  bilgileri konum hesaplaması için Positon'a, gerekirse BeaconDB'ye gönderilir.
- Gizli ağlar ve adı `_nomap` ile biten ağlar sorguya dahil edilmez.
- BeaconDB veri katkısı kapalıdır.
- Bu sürüm internete açık bir merkez sunucusuna konum yayınlamaz.

## Mevcut sürümün sınırları

- Bilgisayar ile web panelini açan cihaz aynı Wi-Fi ağında olmalıdır.
- Bilgisayar açık ve ağa bağlı olmalıdır.
- Harita ve Wi-Fi konum servisleri için internet bağlantısı gerekir.
- Positon'ın prototip `test` anahtarı düşük kullanım limitine sahiptir.
- Farklı ağlardan veya internet üzerinden cihaz bulma henüz etkin değildir.

## Geliştirici kurulumu

Kaynak koddan çalıştırmak için:

```bash
chmod +x run-dev.sh
./run-dev.sh
```

Yerel servis ve web paneli varsayılan olarak şu adreste açılır:

```text
http://127.0.0.1:8765
```

Testleri çalıştırmak için:

```bash
python3 -m unittest discover -s tests -v
```

`.deb` paketi oluşturmak için:

```bash
chmod +x build-deb.sh
./build-deb.sh
```

Oluşturulan paket `build/` dizinine yazılır.

## Proje yapısı

| Yol | Açıklama |
|---|---|
| `src/native_app.py` | GTK masaüstü uygulaması |
| `src/pardus_find/app.py` | Yerel HTTP servisi ve API |
| `src/pardus_find/location.py` | GeoClue, Positon ve BeaconDB konum zinciri |
| `src/pardus_find/web/` | Mobil uyumlu web paneli ve harita |
| `packaging/rootfs/` | Pardus `.deb` paket dosyaları |
| `tests/` | Uygulama ve paketleme testleri |
| `build-deb.sh` | Kurulum paketi oluşturma betiği |

## Yol haritası

- Güvenli HTTPS merkez sunucusuyla farklı ağlardan erişim
- Birden fazla Pardus cihazını tek panelde yönetme
- Son bilinen konum geçmişi
- Cihaz çevrim dışı olduğunda bildirim
- Üretim kullanımı için proje API anahtarı
- Ek güvenlik ve kurum yönetimi seçenekleri

## Kullanılan bileşenler

- Pardus Konum Servisi / GeoClue
- Positon Wi-Fi konum servisi
- BeaconDB
- OpenStreetMap
- Leaflet 1.9.4
- GTK 3
- Python 3

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile yayımlanmaktadır.
