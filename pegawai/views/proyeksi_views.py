from datetime import date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery, Q
from django.core.paginator import Paginator

from pegawai.models import Pegawai, RiwayatKepegawaian


@login_required
def proyeksi_habis_kontrak_view(request):
  mode_filter = request.GET.get('mode', 'rentang')  # 'rentang' atau 'periode'
  bulan_proyeksi = request.GET.get('bulan_rentang', '3')

  tahun_selected = request.GET.get('tahun', '')
  bulan_selected = request.GET.get('bulan', '')
  status_filter = request.GET.get('status_pegawai', '')
  search_query = request.GET.get('q', '').strip()

  today = date.today()

  # 1. Subquery untuk mengambil detail SK/Kontrak TERAKHIR per pegawai
  kontrak_terakhir = RiwayatKepegawaian.objects.filter(
      pegawai=OuterRef('pk'), tmt_selesai__isnull=False
  ).order_by('-tmt', '-created_at')

  # 2. Query Base Pegawai dengan Annotate Subquery
  pegawai_qs = Pegawai.objects.filter(
      status_keaktifan__in=['AKTIF', 'PPPK_PW']
  ).annotate(
      nomor_sk_terakhir=Subquery(kontrak_terakhir.values('nomor_sk')[:1]),
      tmt_mulai_terakhir=Subquery(kontrak_terakhir.values('tmt')[:1]),
      tmt_selesai_terakhir=Subquery(kontrak_terakhir.values('tmt_selesai')[:1]),
      jenis_transaksi_terakhir=Subquery(
          kontrak_terakhir.values('jenis_transaksi')[:1]
      ),
  )

  # 3. Filter berdasarkan mode
  if mode_filter == 'periode' and (tahun_selected or bulan_selected):
    if tahun_selected:
      pegawai_qs = pegawai_qs.filter(
          tmt_selesai_terakhir__year=tahun_selected
      )
    if bulan_selected:
      pegawai_qs = pegawai_qs.filter(
          tmt_selesai_terakhir__month=bulan_selected
      )
  else:
    bln_int = int(bulan_proyeksi) if bulan_proyeksi.isdigit() else 3
    batas_akhir = today + relativedelta(months=bln_int)
    pegawai_qs = pegawai_qs.filter(
        tmt_selesai_terakhir__gte=today, tmt_selesai_terakhir__lte=batas_akhir
    )

  # Filter Kategori Pegawai
  if status_filter == 'PPPK':
    pegawai_qs = pegawai_qs.filter(status_keaktifan='AKTIF')
  elif status_filter == 'PPPK_PW':
    pegawai_qs = pegawai_qs.filter(status_keaktifan='PPPK_PW')

  # Filter Pencarian Nama / NIP
  if search_query:
    pegawai_qs = pegawai_qs.filter(
        Q(nama_lengkap__icontains=search_query)
        | Q(nip__icontains=search_query)
    )

  # Urutkan berdasarkan TMT Selesai terdekat
  pegawai_qs = pegawai_qs.order_by('tmt_selesai_terakhir')

  # 4. SERVER-SIDE PAGINATION: Lakukan Paginator Langsung ke Queryset (Bukan ke Python List)
  paginator = Paginator(
      pegawai_qs, 10
  )  # Ambil database khusus 10 data per halaman
  page_number = request.GET.get('page')
  page_obj = paginator.get_page(page_number)

  # 5. Hitung sisa hari HANYA untuk 10 data yang tampil di halaman aktif saat ini
  data_proyeksi = []
  for p in page_obj:
    sisa_hari = (
        (p.tmt_selesai_terakhir - today).days
        if p.tmt_selesai_terakhir
        else 0
    )
    data_proyeksi.append({
        'pegawai': p,
        'nomor_sk': p.nomor_sk_terakhir,
        'tmt_mulai': p.tmt_mulai_terakhir,
        'tmt_selesai': p.tmt_selesai_terakhir,
        'jenis_transaksi': p.jenis_transaksi_terakhir,
        'sisa_hari': sisa_hari,
    })

  # Buat objek pengganti page_obj untuk iterasi di template agar variabel 'proyeksi_list' tetap kompatibel
  # Atau Anda bisa langsung meloloskan page_obj dan menyesuaikan sedikit kodenya di HTML.
  # Di sini kita buat wrapper paginator agar aman untuk HTML Anda:
  class PageObjectWrapper:

    def __init__(self, page_instance, processed_data):
      self.page_instance = page_instance
      self.object_list = processed_data

    def __iter__(self):
      return iter(self.object_list)

    def __len__(self):
      return len(self.object_list)

    def __bool__(self):
      return bool(self.object_list)

    # Teruskan fungsi-fungsi paginator bawaan
    def has_next(self):
      return self.page_instance.has_next()

    def has_previous(self):
      return self.page_instance.has_previous()

    def has_other_pages(self):
      return self.page_instance.has_other_pages()

    def next_page_number(self):
      return self.page_instance.next_page_number()

    def previous_page_number(self):
      return self.page_instance.previous_page_number()

    def number(self):
      return self.page_instance.number

    @property
    def paginator(self):
      return self.page_instance.paginator

    def __getattr__(self, name):
      return getattr(self.page_instance, name)

  proyeksi_wrapped = PageObjectWrapper(page_obj, data_proyeksi)

  tahun_now = today.year
  list_tahun = range(tahun_now - 1, tahun_now + 6)

  context = {
      'title': 'Proyeksi PPPK Habis Kontrak',
      'proyeksi_list': proyeksi_wrapped,
      'mode_filter': mode_filter,
      'bulan_proyeksi': bulan_proyeksi,
      'tahun_selected': tahun_selected,
      'bulan_selected': bulan_selected,
      'status_filter': status_filter,
      'search_query': search_query,
      'list_tahun': list_tahun,
      'total_pegawai': paginator.count,  # Total keseluruhan data asli dari database (efisien)
      'today': today,
  }
  return render(request, 'pegawai/proyeksi_habis_kontrak.html', context)