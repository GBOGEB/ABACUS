# Independent oracle: PowerPoint's own object model reports effective geometry and fonts. Read-only.
# Usage: pwsh -File ppt_com_oracle.ps1 <deck.pptx> <out.json> [-Png <dir>]
param([string]$Deck, [string]$Out, [string]$Png = "")
$ErrorActionPreference = "Stop"
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open((Resolve-Path $Deck).Path, -1, 0, 0)  # ReadOnly, Untitled=false, WithWindow=false
$PT_MM = 25.4 / 72.0
$rows = New-Object System.Collections.ArrayList
function Visit($shape, $slideNo, $depth) {
    $font = $null; $declared = $null
    try { if ($shape.HasTextFrame -and $shape.TextFrame.HasText) { $font = $shape.TextFrame.TextRange.Runs(1).Font.Name; $declared = $shape.TextFrame2.TextRange.Runs(1).Font.Name } } catch {}
    [void]$rows.Add([ordered]@{ slide = $slideNo; name = $shape.Name; id = $shape.Id; type = [int]$shape.Type; depth = $depth;
        left_mm = [math]::Round($shape.Left * $PT_MM, 3); top_mm = [math]::Round($shape.Top * $PT_MM, 3);
        width_mm = [math]::Round($shape.Width * $PT_MM, 3); height_mm = [math]::Round($shape.Height * $PT_MM, 3);
        rotation = [math]::Round($shape.Rotation, 3); hflip = [int]$shape.HorizontalFlip; vflip = [int]$shape.VerticalFlip;
        font = $font; font2 = $declared })
    if ($shape.Type -eq 6) { foreach ($c in $shape.GroupItems) { if ($c.ParentGroup.Name -eq $shape.Name) { } ; Visit $c $slideNo ($depth + 1) } }
}
try {
    foreach ($s in $pres.Slides) {
        foreach ($sh in $s.Shapes) { Visit $sh $s.SlideIndex 0 }
        if ($Png) { $s.Export((Join-Path $Png ("slide{0:D2}.png" -f $s.SlideIndex)), "PNG", 1280, 720) }
    }
    $meta = [ordered]@{ oracle = "PowerPoint COM " + $pp.Version; slide_w_mm = [math]::Round($pres.PageSetup.SlideWidth * $PT_MM, 3); slide_h_mm = [math]::Round($pres.PageSetup.SlideHeight * $PT_MM, 3); shapes = $rows }
    $meta | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $Out
} finally { $pres.Close(); if ($pp.Presentations.Count -eq 0) { $pp.Quit() } }
