# habbo-dev-env

A declarative, isolated local development environment for Habbo Retros. Runs Nginx, PHP, MySQL, and the emulator via Nix/Devenv without global system modifications.

## Upstreams
* [Orion CMS](https://github.com/Orion-Server/cms) (Laravel 10 / Vue / Node 20)
* [Arcturus Emulator](https://git.krews.org/morningstar/Arcturus-Community) (Java / JDK 21)

## Usage

Requires Nix with Flakes enabled.

```bash
git clone <repo-url> habbo-dev
cd habbo-dev

# Drop into the environment (provisions Nginx, PHP, Node, Java)
nix develop

# Start all services (Web server, DB, Emulator)
devenv up
