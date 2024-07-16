param (
    [Parameter(Mandatory=$true)]
    [string]$Command,
    [string]$Argument
)

$SRC_DIR = "src"

function copy-settings {
    Write-Output "Copying device.json to remote device"
    mpremote fs cp device.json :device.json
}

function copy-dependencies {
    Write-Output "Copying dependencies to remote device"
    $jsonContent = Get-Content -Path "lib/micropython-mqtt/package.json" -Raw
    $jsonObject = $jsonContent | ConvertFrom-Json

    $files = $jsonObject.urls
    $files | ForEach-Object {
        $_[1] = $_[1] -replace "github:peterhinch/", ""
        $src = "lib/" + $_[1]
        $dst = ":" + $_[0]
        mpremote fs cp $src $dst
    }
    Copy-Item lib/micropython-async/v3/primitives/queue.py src/aio_queue.py
    mpremote fs cp lib/micropython-async/v3/primitives/queue.py :aio_queue.py
}

function copy-src {
    Write-Output "Copying ./src/* to remote device"
    Get-ChildItem -Path $SRC_DIR -Recurse | ForEach-Object {
        if ($_.Name -eq "queue.py") {
            return
        }
        $file = "src/" + $_.Name
        $dst = ":" + $_.Name
        mpremote fs cp $file $dst
    }
}

function reset {
    Write-Output "Resetting device"
    mpremote reset
}

function clean {
    $counter = 0
    Write-Output "Removing files from remote device"
    mpremote fs ls | ForEach-Object {
        $counter++
        
        if ($counter -eq 1) {
            return
        }
        
        $file = ":" + $_.Trim() -split '\s+' | Select-Object -Last 1
        
        if ($file -eq ":") {
            return
        }
        mpremote.exe fs rm $file
    }
    reset
}

function run {
    reset
    Start-Sleep -Seconds 2
    copy-src
    mpremote run src/main.py
}

function list {
    mpremote fs ls
}

function build {
    copy-settings
    copy-dependencies
    copy-src
    reset
}

function get {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Filename
    )
    $src = ":" + $Filename
    mpremote fs cp $src $Filename
}

function send {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Filename
    )
    $dst = ":" + $Filename
    mpremote fs cp $Filename $dst
}

switch ($Command) {
    "copy-src" { copy-src } # upload only src files to pico
    "reset" { reset } # reset pico
    "clean" { clean } # delete all files on pico
    "run" { run } # upload only src files and reset pico
    "list" { list } # list all files on pico
    "build" { build } # upload everything and reset pico
    "get" { get $Argument } # retrieve file from pico
    "send" { send $Argument } # retrieve file from pico
    default { Write-Host "Check build.ps1 for available commands" }
}