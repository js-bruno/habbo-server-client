{ pkgs, config, lib, ... }:

{
  devenv.root = let 
    env_root = builtins.getEnv "PWD"; 
  in 
    if env_root != "" then env_root else "./";

  # 1. Pacotes disponíveis no seu terminal quando rodar o shell
  packages = [ 
    pkgs.nodejs_24
    pkgs.yarn 
    pkgs.jdk21 # Java para o Arcturus (Mude para jdk17 se o Arcturus exigir versão mais antiga)
  ];

  # 2. Configuração do PHP 8.2 (Motor do Orion CMS)
  languages.php = {
    enable = true;
    version = "8.3";
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
          listen 8090; # O CMS vai rodar em http://localhost:8090 (troque este número se precisar)
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

  # 4. Subir um MySQL local isolado para o desenvolvimento, já com o schema importado
  services.mysql = {
    enable = true;
    initialDatabases = [
      {
        name = "ms"; # precisa bater com db.database no config.ini
        schema = ./arcturus/base_arcturus.sql;
      }
    ];
  };

  # 5. Gera o config.ini automaticamente e instala dependências do CMS se necessário
  enterShell = ''
    if [ ! -f "${config.env.DEVENV_ROOT}/arcturus/config.ini" ]; then
      cat > "${config.env.DEVENV_ROOT}/arcturus/config.ini" <<'EOF'
#Arcturus Morningstar 3.5.5 - gerado automaticamente pelo devenv

db.hostname=127.0.0.1
db.port=3306
db.database=ms
db.username=root
db.password=
db.params=
db.pool.minsize=25
db.pool.maxsize=100

game.host=0.0.0.0
game.port=3000

rcon.host=127.0.0.1
rcon.port=3001
rcon.allowed=127.0.0.1;127.0.0.2

enc.enabled=false
enc.e=3
enc.n=86851dd364d5c5cece3c883171cc6ddc5760779b992482bd1e20dd296888df91b33b936a7b93f06d29e8870f703a216257dec7c81de0058fea4cc5116f75e6efc4e9113513e45357dc3fd43d4efab5963ef178b78bd61e81a14c603b24c8bcce0a12230b320045498edc29282ff0603bc7b7dae8fc1b05b52b2f301a9dc783b7
enc.d=59ae13e243392e89ded305764bdd9e92e4eafa67bb6dac7e1415e8c645b0950bccd26246fd0d4af37145af5fa026c0ec3a94853013eaae5ff1888360f4f9449ee023762ec195dff3f30ca0b08b8c947e3859877b5d7dced5c8715c58b53740b84e11fbc71349a27c31745fcefeeea57cff291099205e230e0c7c27e8e1c0512b
EOF
      echo "[devenv] config.ini criado automaticamente (root sem senha, banco 'ms')"
    fi

    if [ ! -d "${config.env.DEVENV_ROOT}/cms/vendor" ]; then
      echo "[devenv] Instalando dependências do CMS (composer install)..."
      (cd "${config.env.DEVENV_ROOT}/cms" && composer install)
    fi

    if [ ! -d "${config.env.DEVENV_ROOT}/cms/node_modules" ] && [ -f "${config.env.DEVENV_ROOT}/cms/package.json" ]; then
      echo "[devenv] Instalando dependências do frontend do CMS (yarn install)..."
      (cd "${config.env.DEVENV_ROOT}/cms" && yarn install)
    fi
  '';

  # 6. Comandos utilitários disponíveis dentro do shell (digite o nome direto no terminal)
  scripts.arcturus-reset-config.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    echo "[reset] config.ini removido. Ele será recriado automaticamente na próxima entrada do shell (saia e rode 'nix develop --impure' de novo, ou rode 'devenv shell' novamente)."
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

  scripts.arcturus-full-reset.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    rm -rf "${config.env.DEVENV_ROOT}/.devenv/state/mysql"
    echo "[reset] config.ini e banco resetados. Rode 'devenv up' para subir tudo do zero."
  '';

  scripts.cms-install.exec = ''
    cd "${config.env.DEVENV_ROOT}/cms"
    composer install
    if [ -f package.json ]; then
      yarn install
    fi
    echo "[cms-install] Dependências instaladas."
  '';

  # 7. Iniciar o Emulador Arcturus automaticamente
  processes.arcturus = {
    exec = "cd ${config.env.DEVENV_ROOT}/arcturus && java -jar Habbo-3.5.5-jar-with-dependencies.jar";
    process-compose = {
      depends_on.mysql.condition = "process_healthy";
    };
  };
}
