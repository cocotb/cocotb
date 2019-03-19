FROM mcr.microsoft.com/windowsservercore:1803

SHELL ["PowerShell", "-Command", "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'Continue'; $verbosePreference='Continue';"]

COPY . /src
WORKDIR "c:\src"

RUN Invoke-WebRequest -outfile miniconda3.exe https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe
RUN Start-Process .\miniconda3.exe -ArgumentList '/S /D=C:\miniconda3' -Wait
RUN [System.Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\miniconda3;C:\miniconda3\Library\mingw-w64\bin;C:\miniconda3\Library\usr\bin;C:\miniconda3\Library\bin;C:\miniconda3\Scripts;C:\miniconda3\bin;C:\miniconda3\condabin', 'Machine')
RUN conda install --yes -c msys2 m2-base m2-make m2w64-toolchain libpython

RUN Invoke-WebRequest -Uri http://bleyer.org/icarus/iverilog-10.1.1-x64_setup.exe -OutFile iverilog-10.1.1-x64_setup.exe
RUN Start-Process .\iverilog-10.1.1-x64_setup -ArgumentList '/VERYSILENT' -Wait
RUN [System.Environment]::SetEnvironmentVariable('Path', $env:Path+';C:\iverilog\bin', 'Machine')
