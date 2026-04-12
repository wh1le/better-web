{
  description = "better-web - search, scrape, read";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      libs = pkgs.lib.makeLibraryPath [
        pkgs.stdenv.cc.cc
        pkgs.zlib
        pkgs.glib
        pkgs.nss
        pkgs.nspr
        pkgs.atk
        pkgs.at-spi2-atk
        pkgs.xorg.libX11
        pkgs.xorg.libxcb
        pkgs.cups
        pkgs.libdrm
        pkgs.gtk3
        pkgs.pango
        pkgs.cairo
        pkgs.mesa
        pkgs.expat
        pkgs.libxkbcommon
        pkgs.alsa-lib
        pkgs.dbus
        pkgs.xorg.libXcomposite
        pkgs.xorg.libXdamage
        pkgs.xorg.libXext
        pkgs.xorg.libXfixes
        pkgs.xorg.libXrandr
        pkgs.at-spi2-core
        pkgs.fzf
      ];
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          pkgs.python312
          pkgs.poetry
          pkgs.playwright-driver.browsers
        ];

        shellHook = ''
          export LD_LIBRARY_PATH="${libs}:$LD_LIBRARY_PATH"
          export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
          export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
          export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
          export TRANSFORMERS_VERBOSITY=error
        '';
      };
    };
}
