@echo off
REM ===========================================================
REM  Inglemoor football - local preview
REM
REM  Double-click this to see the site exactly as it will look
REM  online, before you commit anything.
REM
REM  Uses PowerShell, which is built into Windows. Nothing to
REM  install. A black window opens and stays open - that is the
REM  little web server. Close it when you are finished.
REM ===========================================================

title Inglemoor football - preview server
cd /d "%~dp0"

echo.
echo   ===========================================================
echo.
echo     The site will be at:   http://localhost:8000/
echo     The admin page is at:  http://localhost:8000/admin.html
echo.
echo     Your browser should open in a moment.
echo.
echo     KEEP THIS WINDOW OPEN while you look around.
echo     Close it when you are done.
echo.
echo   ===========================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = (Get-Location).Path;" ^
  "$listener = New-Object System.Net.HttpListener;" ^
  "$listener.Prefixes.Add('http://localhost:8000/');" ^
  "try { $listener.Start() } catch { Write-Host '  Could not start on port 8000 - is a preview already running?'; exit 1 };" ^
  "Start-Process 'http://localhost:8000/';" ^
  "$types = @{ '.html'='text/html'; '.css'='text/css'; '.js'='application/javascript';" ^
  "  '.json'='application/json'; '.jpg'='image/jpeg'; '.jpeg'='image/jpeg'; '.png'='image/png';" ^
  "  '.gif'='image/gif'; '.webp'='image/webp'; '.svg'='image/svg+xml'; '.ico'='image/x-icon';" ^
  "  '.mp4'='video/mp4'; '.txt'='text/plain'; '.md'='text/plain' };" ^
  "while ($listener.IsListening) {" ^
  "  try { $ctx = $listener.GetContext() } catch { break };" ^
  "  $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'));" ^
  "  if ([string]::IsNullOrEmpty($rel)) { $rel = 'index.html' };" ^
  "  $file = Join-Path $root ($rel -replace '/', '\\');" ^
  "  if ((Test-Path $file -PathType Leaf) -and $file.StartsWith($root)) {" ^
  "    $ext = [IO.Path]::GetExtension($file).ToLower();" ^
  "    $ctype = $types[$ext]; if (-not $ctype) { $ctype = 'application/octet-stream' };" ^
  "    $bytes = [IO.File]::ReadAllBytes($file);" ^
  "    $ctx.Response.ContentType = $ctype;" ^
  "    $ctx.Response.ContentLength64 = $bytes.Length;" ^
  "    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length);" ^
  "  } else { $ctx.Response.StatusCode = 404 };" ^
  "  $ctx.Response.Close();" ^
  "}"

echo.
echo   Preview stopped.
pause
