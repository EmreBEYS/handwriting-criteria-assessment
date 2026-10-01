# Model Çıktılarının Tanımı

Modelin ilk sürümde çıkardığı alanlar yalnızca şunlardır:

- sınav kâğıdındaki öğrenci numarası,
- sınav tanımındaki her dinamik soru için yazılmış sayısal puan,
- görüntü kalite uyarıları,
- her alan için `[0,1]` aralığında güven skoru.

Model öğrencinin cevabının akademik doğruluğunu, kişiliğini, yeteneğini veya
başka bir özelliğini yorumlamaz. Ground truth, öğretim elemanının doğruladığı
öğrenci numarası ve soru puanıdır. Belirsiz, okunmayan, puan aralığı dışındaki
veya şablonla eşleşmeyen alanlar tahmin uydurmak yerine insan incelemesine
gönderilir.

Her yeni kâğıt şablonu/model sürümü için alan koordinatları, izin verilen değer,
örnekler, güven eşiği ve başarısızlık davranışı sürümlü olarak kaydedilmelidir.
