# Creates the .env file from .env.example with random passwords (first run only).
$katalog = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$plik = Join-Path $katalog '.env'
if (Test-Path $plik) { exit 0 }
$wzor = [IO.File]::ReadAllText((Join-Path $katalog '.env.example'), [Text.Encoding]::UTF8)
function Losowy([int]$n) {
    $b = New-Object byte[] $n
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    return ([Convert]::ToBase64String($b) -replace '[+/=]', '')
}
$wzor = $wzor.Replace('DJANGO_SECRET_KEY=ZMIEN_MNIE', 'DJANGO_SECRET_KEY=' + (Losowy 48))
$wzor = $wzor.Replace('POSTGRES_PASSWORD=ZMIEN_MNIE', 'POSTGRES_PASSWORD=' + (Losowy 24))
[IO.File]::WriteAllText($plik, $wzor, (New-Object Text.UTF8Encoding $false))
Write-Host '>> .env created with random passwords.'
