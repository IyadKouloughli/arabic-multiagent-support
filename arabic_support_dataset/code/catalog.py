# -*- coding: utf-8 -*-
# sku, ar, fr, en, category, price_usd
ITEMS = [
 ("EL-101","سماعات بلوتوث","écouteurs Bluetooth","Bluetooth earbuds","electronics",25),
 ("EL-102","هاتف سامسونج Galaxy A15","téléphone Samsung Galaxy A15","Samsung Galaxy A15 phone","electronics",160),
 ("EL-103","شاحن سريع 65 واط","chargeur rapide 65W","65W fast charger","electronics",20),
 ("EL-104","باور بانك 20000","power bank 20000","20000 power bank","electronics",28),
 ("EL-105","ساعة ذكية","montre connectée","smartwatch","electronics",55),
 ("EL-106","لابتوب لينوفو IdeaPad","PC portable Lenovo IdeaPad","Lenovo IdeaPad laptop","electronics",480),
 ("EL-107","تابلت 10 بوصة","tablette 10 pouces","10-inch tablet","electronics",210),
 ("EL-108","ماوس لاسلكي","souris sans fil","wireless mouse","electronics",12),
 ("AP-201","خلاط كهربائي","mixeur électrique","electric blender","appliance",45),
 ("AP-202","غلاية كهربائية","bouilloire électrique","electric kettle","appliance",22),
 ("AP-203","مكنسة كهربائية","aspirateur","vacuum cleaner","appliance",120),
 ("AP-204","مروحة مكتبية","ventilateur de bureau","desk fan","appliance",30),
 ("HM-301","طقم أواني طهي","set de casseroles","cookware set","home",70),
 ("FA-401","حذاء رياضي","baskets","running shoes","fashion",40),
 ("FA-402","قميص قطني","chemise en coton","cotton shirt","fashion",15),
 ("FA-403","فستان سهرة","robe de soirée","evening dress","fashion",65),
 ("FA-404","جاكيت شتوي","veste d'hiver","winter jacket","fashion",58),
 ("FA-405","حقيبة يد","sac à main","handbag","fashion",36),
 ("HY-501","ملابس داخلية (طقم)","sous-vêtements (lot)","underwear pack","hygiene",12),
 ("GR-601","قهوة عربية","café arabe","Arabic coffee","grocery",10),
 ("GR-602","تمور فاخرة","dattes premium","premium dates","grocery",14),
 ("DG-701","بطاقة هدايا رقمية","carte cadeau numérique","digital gift card","digital",25),
 ("BK-801","كتاب برمجة بايثون","livre Python","Python programming book","books",18),
 ("TY-901","لعبة أطفال تعمل بالبطارية","jouet à piles","battery-powered toy","toys",18),
 ("BT-951","عطر رجالي","parfum homme","men's perfume","beauty",45),
 ("BT-952","مجموعة عناية بالبشرة","coffret soin visage","skincare set","beauty",32),
]
NON_RETURNABLE_CATS = {"hygiene", "grocery", "digital"}
WARRANTY_CATS = {"electronics", "appliance"}

PROMOS = {
 "WELCOME10": {"percent": 10, "valid_until": "2026-12-31", "min_cart_usd": 20, "first_order_only": True},
 "BACK2SCHOOL": {"percent": 15, "valid_until": "2026-09-30", "min_cart_usd": 30, "first_order_only": False},
 "RAMADAN25": {"percent": 25, "valid_until": "2026-03-31", "min_cart_usd": 40, "first_order_only": False},
 "SUMMER15": {"percent": 15, "valid_until": "2026-08-31", "min_cart_usd": 25, "first_order_only": False},
}
UNKNOWN_CODES = ["WELCOM10", "SAVE20", "EID30", "NAWRAS50", "FREESHIP", "VIP2026"]

# country: ar name, currency (ar word, code), usd->local rate, payment methods, varieties
COUNTRIES = {
 "DZ": {"ar": "الجزائر", "cur_ar": "دج", "cur": "DZD", "rate": 135, "pay": ["cod", "edahabia", "card"], "var": ["dz", "dz_fr", "msa"]},
 "EG": {"ar": "مصر", "cur_ar": "جنيه", "cur": "EGP", "rate": 50, "pay": ["cod", "card", "fawry"], "var": ["egy", "msa", "en_mix"]},
 "SA": {"ar": "السعودية", "cur_ar": "ريال", "cur": "SAR", "rate": 3.75, "pay": ["mada", "card", "cod", "apple_pay"], "var": ["glf", "msa", "en_mix"]},
 "AE": {"ar": "الإمارات", "cur_ar": "درهم", "cur": "AED", "rate": 3.67, "pay": ["card", "cod", "apple_pay"], "var": ["glf", "en_mix", "msa"]},
 "JO": {"ar": "الأردن", "cur_ar": "دينار", "cur": "JOD", "rate": 0.71, "pay": ["cod", "card", "cliq"], "var": ["lev", "msa", "en_mix"]},
 "LB": {"ar": "لبنان", "cur_ar": "دولار", "cur": "USD", "rate": 1, "pay": ["cod", "card"], "var": ["lev", "msa", "en_mix"]},
 "MA": {"ar": "المغرب", "cur_ar": "درهم", "cur": "MAD", "rate": 10, "pay": ["cod", "card"], "var": ["msa"]},
 "TN": {"ar": "تونس", "cur_ar": "دينار", "cur": "TND", "rate": 3.1, "pay": ["cod", "card"], "var": ["msa", "en_mix"]},
}
CARD_LIKE = {"card", "mada", "apple_pay", "edahabia", "fawry", "cliq"}

ADDRESSES = {
 "DZ": [("حي 5 جويلية، وهران", "Cité 5 Juillet, Oran"), ("شارع ديدوش مراد، الجزائر العاصمة", "Rue Didouche Mourad, Alger"), ("حي بومعراف، قسنطينة", "Cité Boumaraf, Constantine"), ("حي النصر، عنابة", "Cité El Nasr, Annaba"), ("حي السلام، سطيف", "Cité Es Salam, Sétif")],
 "EG": [("شارع التسعين، القاهرة الجديدة", "90th Street, New Cairo"), ("كورنيش المعادي، القاهرة", "Corniche El Maadi, Cairo"), ("شارع سموحة، الإسكندرية", "Smouha, Alexandria"), ("مدينة نصر، القاهرة", "Nasr City, Cairo"), ("شارع الهرم، الجيزة", "Haram Street, Giza")],
 "SA": [("حي الملقا، الرياض", "Al Malqa, Riyadh"), ("حي الروضة، جدة", "Al Rawdah, Jeddah"), ("حي العزيزية، الخبر", "Al Aziziyah, Khobar"), ("حي النزهة، الدمام", "Al Nuzha, Dammam")],
 "AE": [("مرسى دبي، دبي", "Dubai Marina, Dubai"), ("الخالدية، أبوظبي", "Khalidiyah, Abu Dhabi"), ("الممزر، الشارقة", "Al Mamzar, Sharjah")],
 "JO": [("دابوق، عمّان", "Dabouq, Amman"), ("الجبيهة، عمّان", "Jubeiha, Amman"), ("وسط البلد، إربد", "Downtown, Irbid")],
 "LB": [("الحمرا، بيروت", "Hamra, Beirut"), ("الجديدة، المتن", "Jdeideh, Metn"), ("وسط زحلة", "Central Zahle")],
 "MA": [("المعاريف، الدار البيضاء", "Maarif, Casablanca"), ("أكدال، الرباط", "Agdal, Rabat"), ("جيليز، مراكش", "Gueliz, Marrakech")],
 "TN": [("المنزه، تونس", "El Menzah, Tunis"), ("وسط سوسة", "Central Sousse"), ("وسط صفاقس", "Central Sfax")],
}
# (ar, latin) first names and last names per country
NAMES = {
 "DZ": ([("محمد","Mohamed"),("يوسف","Youcef"),("رياض","Riad"),("أمينة","Amina"),("ليلى","Leila"),("سمية","Soumia")], [("بن عيسى","Benaissa"),("بوزيد","Bouzid"),("مزياني","Meziani"),("قاسمي","Kassemi"),("زروقي","Zerrouki")]),
 "EG": ([("أحمد","Ahmed"),("مصطفى","Mostafa"),("كريم","Karim"),("منى","Mona"),("نورا","Noura"),("ياسمين","Yasmin")], [("الشافعي","Elshafei"),("حسن","Hassan"),("السيد","Elsayed"),("فتحي","Fathy"),("عيد","Eid")]),
 "SA": ([("عبدالله","Abdullah"),("فهد","Fahad"),("تركي","Turki"),("نورة","Noura"),("سارة","Sara"),("ريم","Reem")], [("العتيبي","Alotaibi"),("الغامدي","Alghamdi"),("القحطاني","Alqahtani"),("الشمري","Alshammari"),("الدوسري","Aldosari")]),
 "AE": ([("سالم","Salem"),("ناصر","Nasser"),("خالد","Khaled"),("مريم","Maryam"),("شيخة","Shaikha"),("موزة","Moza")], [("المنصوري","Almansoori"),("الكعبي","Alkaabi"),("النعيمي","Alnuaimi"),("الظاهري","Aldhaheri")]),
 "JO": ([("عمر","Omar"),("ليث","Laith"),("طارق","Tareq"),("رنا","Rana"),("دانا","Dana"),("هبة","Heba")], [("الخطيب","Alkhatib"),("العمري","Alomari"),("الزعبي","Alzoubi"),("النابلسي","Nabulsi")]),
 "LB": ([("جاد","Jad"),("كريم","Karim"),("ريما","Rima"),("ميراي","Mireille"),("سامر","Samer"),("لينا","Lina")], [("خوري","Khoury"),("حداد","Haddad"),("نصر","Nasr"),("صعب","Saab")]),
 "MA": ([("ياسين","Yassine"),("أيوب","Ayoub"),("سلمى","Salma"),("هند","Hind"),("زينب","Zineb")], [("العلوي","Alaoui"),("الإدريسي","Idrissi"),("التازي","Tazi"),("المراني","Marrani")]),
 "TN": ([("أنيس","Anis"),("وسيم","Wassim"),("ياسمين","Yasmine"),("ريم","Rym"),("سنية","Sonia")], [("بن سالم","Ben Salem"),("الطرابلسي","Trabelsi"),("المبروك","Mabrouk"),("الجبالي","Jebali")]),
}
CARRIERS = ["Barq Express", "SwiftBox", "Rawa7 Delivery", "Yalla Ship"]
INTENT_LIST = ["order_status", "cancel_order", "return_request", "damaged", "double_charge", "address_change",
               "delivery_delay", "promo", "warranty", "account_change", "complaint", "faq"]
