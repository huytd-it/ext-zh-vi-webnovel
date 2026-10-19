; Release engineer supplies NVIDIA redistributables and their license texts only after review.
; Compile separately; never included in CPU installer.
#ifndef CudaSource
  #error Define CudaSource to a reviewed directory of CUDA 12 redistributables and LICENSE files.
#endif
[Setup]
AppId={{A7FA136C-0920-4E89-B478-713F18817536}
AppName=Novel Local NVIDIA dependencies
AppVersion=0.1.0
DefaultDirName={localappdata}\NovelLocal\cuda
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\artifacts
OutputBaseFilename=NovelLocal-NVIDIA-dependencies-0.1.0
Compression=lzma2
[Files]
Source: "{#CudaSource}\cublas64_12.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#CudaSource}\cublasLt64_12.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#CudaSource}\cudart64_12.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#CudaSource}\LICENSE*"; DestDir: "{app}"; Flags: ignoreversion
