{ pkgs, config, lib, ... }:

{
  # 1. Pacotes disponíveis no seu terminal quando rodar o shell
  packages = [ 
    pkgs.nodejs_20 
    pkgs.yarn 
    pkgs.jdk21 # Java para o Arcturus (Mude para jdk17 se o Arcturus exigir versão mais antiga)
  ];

  # 2. Configuração do PHP 8.2 (Motor do Orion CMS)
  languages.php = {
    enable = true;
    version = "8.2";
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

  # 3. Configuração do Nginx
  services.nginx = {
    enable = true;
    httpConfig = ''
      server {
          listen 8080; # O CMS vai rodar em http://localhost:8080
          server_name localhost;
          
          # Aponta diretamente para a pasta local dentro do seu projeto
          root ${config.env.DEVENV_ROOT}/cms/public;

          add_header X-Frame-Options "SAMEORIGIN";
          add_header X-XSS-Protection "1; mode=block";
          add_header X-Content-Type-Options "nosniff";

          index index.php;
          charset utf-8;

          location / {
              try_files $uri $uri/ /index.php?$query_string;
          }

          location = /favicon.ico { access_log off; log_not_found off; }
          location = /robots.txt  { access_log off; log_not_found off; }
          error_page 404 /index.php;

          # Conecta o Nginx ao PHP configurado acima
          location ~ \.php$ {
              fastcgi_pass unix:${config.languages.php.fpm.pools.orion.socket};
              fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
              include ${pkgs.nginx}/conf/fastcgi_params;
          }

          location ~ /\.(?!well-known).* {
              deny all;
          }
      }
    '';
  };

  # 4. (Opcional) Subir um MySQL local isolado apenas para o desenvolvimento
  services.mysql = {
    enable = true;
    initialDatabases = [{ name = "habbo_db"; }];
  };

  # 5. Iniciar o Emulador Arcturus automaticamente
  processes.arcturus.exec = "java -jar ${config.env.DEVENV_ROOT}/arcturus/HabboEmulator.jar";
  # Nota: Substitua 'HabboEmulator.jar' pelo nome exato do arquivo .jar do seu emulador.
}
