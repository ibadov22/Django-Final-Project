# Məqalə — Django final layihəsi

Habr üslubunda məqalə və xəbər platforması. Django 5.2 və Python 3.10+ ilə hazırlanıb.

## Başlatma

1. Layihə qovluğunda terminal açın.
2. Virtual mühit yaradıb aktivləşdirin:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
3. Asılılıqları və verilənlər bazasını hazırlayın:

   ```powershell
   python -m pip install -r requirements.txt
   python manage.py migrate
   ```
4. Super Admin hesabı yaradın:

   ```powershell
   python manage.py createsuperuser
   ```

   Yaradılan superuser avtomatik olaraq Super Admin roluna malik olur.
5. Saytı başladın:

   ```powershell
   python manage.py runserver
   ```

   Brauzerdə http://127.0.0.1:8000/ ünvanını açın. Django idarəetmə paneli `/django-admin/` ünvanındadır.

## Rollar və icazələr

- **Qonaq:** dərc edilmiş məqalələri və şərhləri oxuya, axtarış edə bilər.
- **İstifadəçi:** qeydiyyatdan sonra məqalə yaradır; öz məqaləsini redaktə/silə bilər. Məqalələr əvvəlcə qaralama kimi saxlanılır, müəllif öz qaralamasını görə bilir.
- **Admin:** məqalələri idarə edir və istifadəçiləri bloklayıb blokdan çıxarır.
- **Super Admin:** Admin imkanlarına əlavə olaraq istifadəçiyə Admin rolunu verir və ya geri alır.

Super Admin hesabı `createsuperuser` ilə yaradılır; yeni qeydiyyatçılar heç vaxt imtiyazlı rol seçə bilmirlər. Bloklanan istifadəçi sistemə daxil ola bilmir.

## Məqalə imkanları

Məqalədə başlıq, qısa təsvir, mətn, kateqoriya, teqlər, status (qaralama/dərc edilib), yaradılma və yenilənmə vaxtı saxlanılır. Ana səhifədə axtarış, kateqoriya filtri, sıralama və səhifələmə var. Dərc edilmiş məqalələrə şərh yazmaq üçün giriş tələb olunur.
