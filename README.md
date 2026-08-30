habbo-dev-env
=============

A declarative, isolated local development environment for Habbo Retros. 
Runs Nginx, PHP, MySQL, and the emulator via Nix/Devenv without global system modifications.

Upstreams
---------
* Orion CMS: https://github.com/Orion-Server/cms
* Arcturus Emulator: https://git.krews.org/morningstar/Arcturus-Community

Usage
-----
Requires Nix with Flakes enabled.

$ git clone <repo-url> habbo-dev
$ cd habbo-dev

# Drop into the environment (provisions Nginx, PHP, Node, Java)
$ nix develop

# Start all services (Web server, DB, Emulator)
$ devenv up

The CMS will be available at http://localhost:8080.
Press Ctrl+C to terminate all processes.

Structure
---------
.
├── arcturus/        # Emulator source and .jar
├── cms/             # Orion source
├── devenv.nix       # Service orchestration and routing
└── flake.nix        # Dependency lock
