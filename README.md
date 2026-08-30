<pre>
/*
 * PROJECT: habbo-dev-env
 * DESC:    A declarative, isolated local development environment for Habbo Retros.
 *          Runs Nginx, PHP, MySQL, and the emulator via Nix/Devenv.
 */

[UPSTREAMS]
Orion_CMS         = "[https://github.com/Orion-Server/cms](https://github.com/Orion-Server/cms)"
Arcturus_Emulator = "[https://git.krews.org/morningstar/Arcturus-Community](https://git.krews.org/morningstar/Arcturus-Community)"


[USAGE]
> git clone <repo-url> habbo-dev
> cd habbo-dev

/* Provision Nginx, PHP, Node, Java */
> nix develop

/* Start Web server, DB, Emulator */
> devenv up

OUTPUT:
  Frontend -> http://localhost:8080
  Exit     -> Ctrl+C


[STRUCTURE]
.
|-- arcturus/      /* Emulator source and .jar */
|-- cms/           /* Orion source */
|-- devenv.nix     /* Service orchestration and routing */
`-- flake.nix      /* Dependency lock */
</pre>
