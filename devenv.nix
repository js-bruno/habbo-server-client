{ pkgs, config, lib, ... }:

{
  devenv.root = let 
    env_root = builtins.getEnv "PWD"; 
  in 
    if env_root != "" then env_root else "./";

  packages = [ 
    pkgs.nodejs_24
    pkgs.yarn 
    pkgs.jdk21
    pkgs.maven
  ];

  languages.php = {
    enable = true;
    version = "8.5";
    fpm.pools.orion = {
      settings = {
        "pm" = "dynamic";
        "pm.max_children" = 5;
        "pm.start_servers" = 2;
        "pm.min_spare_servers" = 1;
        "pm.max_spare_servers" = 3;
      };
    };
  };

  services.nginx = {
    enable = true;
    httpConfig = ''
      server {
        listen 80; # O CMS vai rodar em http://localhost:8090 (troque este número se precisar)
          server_name localhost;

        root ${config.env.DEVENV_ROOT}/cms/public;

        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-XSS-Protection "1; mode=block";
        add_header X-Content-Type-Options "nosniff";

        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;

        index index.php;
        charset utf-8;

        location / {
          if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "*" always;
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
            add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
          }

          try_files $uri $uri/ /index.php?$query_string;
        }

        location = /favicon.ico { access_log off; log_not_found off; }
        location = /robots.txt  { access_log off; log_not_found off; }
        error_page 404 /index.php;

        location ~ \.php$ {
          fastcgi_pass unix:${config.languages.php.fpm.pools.orion.socket};
          fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
          include ${pkgs.nginx}/conf/fastcgi_params;

          add_header Access-Control-Allow-Origin "*" always;
        }

        location ~ /\.(?!well-known).* {
          deny all;
        }
      }
    '';
  };
  services.mysql = {
    enable = true;
  };

  enterShell = ''

  '';

  scripts.arcturus-reset-db.exec = ''
    echo "[reset] Isso vai apagar TODO o estado do MySQL do devenv (não afeta MySQL do sistema)."
    read -p "Confirma? (digite 'sim'): " confirm
    if [ "$confirm" = "sim" ]; then
      rm -rf "${config.env.DEVENV_ROOT}/.devenv/state/mysql"
      echo "[reset] Estado do MySQL apagado. Rode 'devenv up' de novo para recriar o banco 'ms' já com o schema base_arcturus.sql importado."
    else
      echo "[reset] Cancelado."
    fi
  '';
  scripts.arcturus-load-schema.exec = ''
    bash "${config.env.DEVENV_ROOT}/helpers/load-schema.sh"
  '';
  scripts.arcturus-full-reset.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    rm -rf "${config.env.DEVENV_ROOT}/.devenv/state/mysql"
    echo "[reset] config.ini e banco resetados. Rode 'devenv up' para subir tudo do zero."
  '';
  scripts.arcturus-reset-config.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    echo "[reset] config.ini removido. Ele será recriado automaticamente na próxima entrada do shell (saia e rode 'nix develop --impure' de novo, ou rode 'devenv shell' novamente)."
  '';

  processes.arcturus = {
    exec = "cd ${config.env.DEVENV_ROOT}/arcturus && java -jar Habbo-3.5.5-jar-with-dependencies.jar";
    process-compose = {
      depends_on.mysql.condition = "process_healthy";
    };
  };
  processes.atom = {
    exec = "cd ${config.env.DEVENV_ROOT}/cms && npm run dev:dusk";
    process-compose = {
      depends_on.mysql.condition = "process_healthy";
    };
  };
  processes.atom-serve = {
    exec = "cd ${config.env.DEVENV_ROOT}/cms && php artisan serve";
    process-compose = {
      depends_on.mysql.condition = "process_healthy";
    };
  };
}
