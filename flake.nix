{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    devenv.url = "github:cachix/devenv";
  };

  outputs = { self, nixpkgs, devenv, ... } @ inputs: {
    devShells.x86_64-linux.default = devenv.lib.mkShell {
      inherit inputs;
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      modules = [ ./devenv.nix ];
    };
  };
}
