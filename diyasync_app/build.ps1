$ErrorActionPreference = "Stop"

$projectDir = "D:\odoo-19.0\scratch\diyasync"
$workDir = "D:\odoo-19.0\scratch\diyasync\build"
$outApk = "D:\odoo-19.0\custom_addons\diyacrm\static\downloads\diyasync.apk"

$jdkHome = "C:\Program Files\Android\Android Studio1\jbr"
$env:JAVA_HOME = $jdkHome
$javac = "$jdkHome\bin\javac.exe"
$jarTool = "$jdkHome\bin\jar.exe"
$keytool = "$jdkHome\bin\keytool.exe"

$sdkDir = "$env:LOCALAPPDATA\Android\Sdk"
$buildTools = "$sdkDir\build-tools\35.0.0"
$androidJar = "$sdkDir\platforms\android-35\android.jar"

Write-Host "=== 1. Preparing Build Directory ==="
if (Test-Path $workDir) { Remove-Item -Recurse -Force $workDir }
New-Item -ItemType Directory -Force "$workDir\classes", "$workDir\gen", "$workDir\dex" | Out-Null

Write-Host "=== 2. Compiling Resources (AAPT2) ==="
& "$buildTools\aapt2.exe" compile --dir "$projectDir\res" -o "$workDir\compiled_res.zip"

Write-Host "=== 3. Linking Resources (AAPT2) ==="
& "$buildTools\aapt2.exe" link -o "$workDir\base.apk" `
    -I $androidJar `
    --manifest "$projectDir\AndroidManifest.xml" `
    "$workDir\compiled_res.zip" `
    --java "$workDir\gen" `
    --auto-add-overlay

Write-Host "=== 4. Compiling Java Source Files ==="
$javaFiles = (Get-ChildItem -Recurse "$projectDir\src", "$workDir\gen" -Filter "*.java").FullName
& $javac -encoding UTF-8 -cp $androidJar -d "$workDir\classes" $javaFiles

Write-Host "=== 5. Converting to Dalvik DEX (D8) ==="
$classFiles = (Get-ChildItem -Recurse "$workDir\classes" -Filter "*.class").FullName
& "$buildTools\d8.bat" --min-api 24 --output "$workDir\dex" $classFiles

Write-Host "=== 6. Packaging DEX and Assets into APK ==="
# Add classes.dex into root of base.apk
Set-Location "$workDir\dex"
& $jarTool -uf "$workDir\base.apk" classes.dex

# Add assets into base.apk
Set-Location "$projectDir"
& $jarTool -uf "$workDir\base.apk" assets

Write-Host "=== 7. Aligning APK (Zipalign) ==="
Set-Location "D:\odoo-19.0"
& "$buildTools\zipalign.exe" -p -f 4 "$workDir\base.apk" "$workDir\aligned.apk"

Write-Host "=== 8. Creating Signing Keystore ==="
$keystore = "$workDir\diya.keystore"
if (-not (Test-Path $keystore)) {
    & $keytool -genkeypair -v -keystore $keystore -alias diya -keyalg RSA -keysize 2048 -validity 10000 `
        -storepass diyacrm123 -keypass diyacrm123 -dname "CN=DiyaCRM, O=Diya, C=IN"
}

Write-Host "=== 9. Signing APK (Apksigner) ==="
New-Item -ItemType Directory -Force (Split-Path $outApk) | Out-Null
& "$buildTools\apksigner.bat" sign `
    --ks $keystore --ks-key-alias diya `
    --ks-pass pass:diyacrm123 --key-pass pass:diyacrm123 `
    --out $outApk "$workDir\aligned.apk"

Write-Host "=== 10. Verifying Signed APK ==="
& "$buildTools\apksigner.bat" verify -v $outApk

$size = (Get-Item $outApk).Length / 1MB
Write-Host "SUCCESS! Built $outApk ($([math]::Round($size, 2)) MB)" -ForegroundColor Green
