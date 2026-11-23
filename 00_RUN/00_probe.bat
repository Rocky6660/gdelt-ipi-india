@echo off
cd /d "%~dp0.."
set LOG=logs\probe_windows.txt
echo PROBE %DATE% %TIME% > %LOG%
where python >> %LOG% 2>&1
where py >> %LOG% 2>&1
python --version >> %LOG% 2>&1
py -3 --version >> %LOG% 2>&1
where gcloud >> %LOG% 2>&1
where bq >> %LOG% 2>&1
where curl >> %LOG% 2>&1
for %%U in (https://data.gdeltproject.org/gdeltv2/lastupdate.txt https://bigquery.googleapis.com https://www.rbi.org.in https://api.mospi.gov.in https://fred.stlouisfed.org https://web.archive.org https://timesofindia.indiatimes.com https://ceda.ashoka.edu.in) do (
  curl -s -o NUL -m 20 -w "%%U %%{http_code}\n" %%U >> %LOG% 2>&1
)
echo DONE >> %LOG%
