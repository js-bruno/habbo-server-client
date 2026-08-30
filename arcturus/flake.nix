{
  description = "Ambiente de desenvolvimento para Arcturus-Community";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      # Altere para "aarch64-linux" se estiver usando um servidor ARM
      system = "x86_64-linux"; 
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          jdk17
          maven
          git
        ];

        shellHook = ''
          echo "Ambiente Nix Flake carregado para o Arcturus-Community!"
          java --version
          mvn --version
        '';
      };
    };
}
