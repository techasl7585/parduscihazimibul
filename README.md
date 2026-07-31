# Pardus Cihazımı Bul

- Pardus Cihazımı Bul, Cihaz Konumunu web paneli üzerinden görüntüleyen açık kaynaklı bir cihazımı bul uygulamasıdır.
- Amaç Pardus Kullanan Cihazlar Kaybolduğunda Kolayca Bulunmasını Sağlamaktır.
 
> Bu sürüm, aynı Wi-Fi ağı içinde çalışan yerel prototiptir.
> İlerleyen Sürümlerde Sunucu Desteği ile İnternet olan her yerde çalışacak sürüme geçilebilir şuan elimde herhangi bir sunucu olmadığı için şimdilik yerel ağ ile hazırlanmıştır.

## Gereksinimler

  - amd64 64 Bit Bilgisayar
  - İnternet Bağlantısı
  - Pardus Gnome
  - Bilgisayar ve konum görüntüleyen cihaz aynı Wi-Fi ağında olması gerekir (ilk sürüm)
    
## Önemli Not
Eğer Konum Düşük hassasiyetle gösterirse uygulama 3 son seçenek olan BeaconDB ile bulmuştur gerçek konuma daha yakın hassas konum için sistemi daha hassas konum olan Positon servisi ile bulana kadar yani doğruluğu yüksek konumu bulana kadar (gerçek konumunuza en yakın konum) yeniden başlatın. Düşük hassasiyet kullanan BeaconDB servisi hiçbiri çalışmazsa yaklaşık konum bulmak için konulmuştur.

### Kurulum

1. [Pardus Cihazımı Bul 0.1.7 `.deb` paketini indirin.](https://github.com/techasl7585/parduscihazimibul/releases/download/v0.1.7/pardus-cihazimi-bul_0.1.7_amd64.deb)
2. İndirilen pakete çift tıklayın.
3. Pardus Paket Kurucu'da **Kur** düğmesine basın.
4. İstendiğinde sistem parolanızı girin.
5. Bilgisayar ve konum görüntüleyen cihaz aynı Wi-Fi ağına bağladıktan sonra (ilk sürüm)
6. Uygulamalar menüsünden **Pardus Cihazımı Bul** uygulamasını açın.

Terminal kullanmak zorunlu değildir. Kurulum paketi gerekli Python, GTK,
GeoClue ve ağ bileşenlerini Pardus depolarından otomatik olarak kurar; arka plan
servisini oluşturur ve sistem başlangıcında etkinleştirir.

İlk kurulum sırasında bağımlılıkların indirilebilmesi için internet bağlantısı
gerekir.


## Ne işe yarar?

- Kullanıcı **Konumumu Paylaş** düğmesine basarak paylaşımı başlatır.
- Bilgisayar kendi konumunu kendi konum kaynaklarıyla belirler ve Konumu Web Panelinde Paylaşır.
- Uygulama web paneli adresini gösterir.
- Web paneli telefon, tablet ve bilgisayar tarayıcılarında açılır. 
- Cihazın Konumu, son görülme zamanı, yerel IP adresi ve konum
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
   gördüğü Wi-Fi erişim noktalarından konum hesaplar. Yüksek Hassasiyet
3. **BeaconDB:** Diğer kaynaklar sonuç üretmezse son yedek konum kaynağı olarak
   kullanılır. Düşük Hassasiyet

