<#
.SYNOPSIS
  Zero-dependency static file server for the dashboard, using .NET's
  HttpListener. Needed because browsers block fetch() of local files opened
  via file:// — Python/Node aren't required to run this, just PowerShell.

.USAGE
  powershell -ExecutionPolicy Bypass -File scripts\serve.ps1
  Then open http://localhost:8000/dashboard/ in a browser.
#>
param(
    [int]$Port = 8000
)

$root = Split-Path -Parent $PSScriptRoot
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "Serving '$root' at http://localhost:$Port/  (Ctrl+C to stop)"
Write-Host "Dashboard: http://localhost:$Port/dashboard/"

$mimeTypes = @{
    ".html" = "text/html"; ".htm" = "text/html"
    ".json" = "application/json"
    ".js"   = "application/javascript"
    ".css"  = "text/css"
    ".py"   = "text/plain"
    ".png"  = "image/png"; ".jpg" = "image/jpeg"; ".svg" = "image/svg+xml"
    ".ico"  = "image/x-icon"
}

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        try {
            $relPath = [Uri]::UnescapeDataString($request.Url.AbsolutePath.TrimStart('/'))
            if ([string]::IsNullOrEmpty($relPath) -or $relPath.EndsWith('/')) {
                $relPath = "$relPath" + "index.html"
            }
            $filePath = Join-Path $root $relPath

            if (Test-Path $filePath -PathType Leaf) {
                $ext = [System.IO.Path]::GetExtension($filePath).ToLower()
                $contentType = if ($mimeTypes.ContainsKey($ext)) { $mimeTypes[$ext] } else { "application/octet-stream" }
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $response.ContentType = $contentType
                $response.ContentLength64 = $bytes.Length
                $response.OutputStream.Write($bytes, 0, $bytes.Length)
            } else {
                $response.StatusCode = 404
                $notFound = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found: $relPath")
                $response.OutputStream.Write($notFound, 0, $notFound.Length)
            }
        } catch {
            $response.StatusCode = 500
            $err = [System.Text.Encoding]::UTF8.GetBytes("500: $_")
            $response.OutputStream.Write($err, 0, $err.Length)
        } finally {
            $response.OutputStream.Close()
        }
    }
} finally {
    $listener.Stop()
}
