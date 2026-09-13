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
    pkgs.git
    pkgs.curl
  ];

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

  services.nginx = {
    enable = true;
    httpConfig = ''
      server {
          listen 8090;
          server_name localhost;
          root ${config.env.DEVENV_ROOT}/cms/public;
          index index.php;
          charset utf-8;

          location / {
              try_files $uri $uri/ /index.php?$query_string;
          }

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

  services.mysql = {
    enable = true;
    initialDatabases = [
      {
        name = "habbo";
        schema = ./arcturus/base_arcturus.sql;
      }
    ];
  };

  enterShell = ''
    set +e
    ROOT="${config.env.DEVENV_ROOT}"
    cd "$ROOT"

    echo ""
    echo "🔧 Verificando setup do servidor Habbo..."

    ARCTURUS_REPO_URL="https://git.krews.org/krews/Morningstar.git"
    if [ ! -d "$ROOT/arcturus/.git" ]; then
      echo "  → Clonando Arcturus Morningstar 3.5.5..."
      git clone "$ARCTURUS_REPO_URL" "$ROOT/arcturus" 2>&1 | tail -5
    fi

    if [ -d "$ROOT/arcturus" ] && [ -f "$ROOT/arcturus/pom.xml" ]; then
      JAR=$(find "$ROOT/arcturus/target" -iname "*-jar-with-dependencies.jar" 2>/dev/null | head -1)
      if [ -z "$JAR" ]; then
        echo "  → Compilando Arcturus (mvn clean package)... isso pode demorar alguns minutos na primeira vez."
        (cd "$ROOT/arcturus" && mvn -q clean package 2>&1 | tail -20)
        JAR=$(find "$ROOT/arcturus/target" -iname "*-jar-with-dependencies.jar" 2>/dev/null | head -1)
      fi
      if [ -n "$JAR" ]; then
        echo "  ✓ Jar do Arcturus pronto: $(basename "$JAR")"
        echo "$JAR" > "$ROOT/.devenv-arcturus-jar"
      else
        echo "  ⚠ Falha ao compilar o Arcturus. Rode manualmente: cd arcturus && mvn clean package"
      fi
    fi

    if [ -d "$ROOT/arcturus" ] && [ ! -f "$ROOT/arcturus/config.ini" ]; then
      echo "  → Gerando arcturus/config.ini..."
      cat > "$ROOT/arcturus/config.ini" <<'EOF'
db.hostname=127.0.0.1
db.port=3306
db.database=habbo
db.username=root
db.password=
db.params=
db.pool.minsize=5
db.pool.maxsize=30

game.host=0.0.0.0
game.port=3000

rcon.host=127.0.0.1
rcon.port=3001
rcon.allowed=127.0.0.1

enc.enabled=false
EOF
      echo "  ✓ config.ini criado (root sem senha, banco 'habbo')"
    fi

    WEBSOCKETS_PLUGIN_REPO_URL="https://git.krews.org/nitro/ms-websockets.git"
    if [ ! -d "$ROOT/ms-websockets/.git" ]; then
      echo "  → Clonando plugin NitroWebsockets..."
      git clone "$WEBSOCKETS_PLUGIN_REPO_URL" "$ROOT/ms-websockets" 2>&1 | tail -5
    fi

    if [ -d "$ROOT/ms-websockets" ] && [ -f "$ROOT/ms-websockets/pom.xml" ]; then
      PLUGIN_JAR=$(find "$ROOT/arcturus/plugins" -iname "*.jar" 2>/dev/null | head -1)
      if [ -z "$PLUGIN_JAR" ] && [ -f "$ROOT/.devenv-arcturus-jar" ]; then
        MAIN_JAR=$(cat "$ROOT/.devenv-arcturus-jar")
        echo "  → Instalando $MAIN_JAR como com.eu.habbo:Habbo:3.0.0 no Maven local..."
        mvn -q install:install-file -Dfile="$MAIN_JAR" -DgroupId=com.eu.habbo -DartifactId=Habbo -Dversion=3.0.0 -Dpackaging=jar 2>&1 | tail -10

        echo "  → Compilando plugin de WebSocket..."
        mkdir -p "$ROOT/arcturus/plugins"
        (cd "$ROOT/ms-websockets" && mvn -q clean package 2>&1 | tail -20)
        NEW_PLUGIN_JAR=$(find "$ROOT/ms-websockets/target" -iname "*.jar" ! -iname "*sources*" 2>/dev/null | head -1)
        if [ -n "$NEW_PLUGIN_JAR" ]; then
          cp "$NEW_PLUGIN_JAR" "$ROOT/arcturus/plugins/"
          echo "  ✓ Plugin instalado em arcturus/plugins/"
        else
          echo "  ⚠ Falha ao compilar o plugin. Verifique manualmente em ms-websockets/"
        fi
      fi
    fi

    if [ -d "$ROOT/cms" ] && [ ! -d "$ROOT/cms/vendor" ]; then
      echo "  → Instalando dependências do CMS (composer install)..."
      (cd "$ROOT/cms" && composer install --no-interaction 2>&1 | tail -15)
    fi

    if [ -d "$ROOT/cms" ] && [ ! -f "$ROOT/cms/.env" ] && [ -f "$ROOT/cms/.env.example" ]; then
      echo "  → Criando cms/.env a partir do .env.example..."
      cp "$ROOT/cms/.env.example" "$ROOT/cms/.env"
      (cd "$ROOT/cms" && php artisan key:generate --force 2>&1 | tail -5)
    fi

    NITRO_DIST="$ROOT/cms/public/client/nitro/nitro-react/dist"
    if [ ! -d "$ROOT/client/nitro/nitro-react/.git" ] && [ ! -d "$NITRO_DIST" ]; then
      echo "  → Clonando nitro-react (versão confirmada funcionando)..."
      mkdir -p "$ROOT/client/nitro"
      git clone https://github.com/billsonnn/nitro-react.git "$ROOT/client/nitro/nitro-react" 2>&1 | tail -5
      (cd "$ROOT/client/nitro/nitro-react" && yarn add @nitrots/nitro-renderer@1.6.6 --silent 2>&1 | tail -10) || true
    fi

    if [ -d "$ROOT/client/nitro/nitro-react" ] && [ ! -d "$ROOT/client/nitro/nitro-react/node_modules" ]; then
      echo "  → Instalando dependências do Nitro (yarn install)..."
      (cd "$ROOT/client/nitro/nitro-react" && yarn install --silent 2>&1 | tail -15)
    fi

    if [ -d "$ROOT/client/nitro/nitro-react" ] && [ ! -d "$ROOT/client/nitro/nitro-react/dist" ]; then
      echo "  → Buildando Nitro (yarn build)..."
      (cd "$ROOT/client/nitro/nitro-react" && yarn build 2>&1 | tail -15)
    fi

    if [ -d "$ROOT/client/nitro/nitro-react/dist" ] && [ ! -d "$NITRO_DIST" ]; then
      echo "  → Copiando build do Nitro para o CMS..."
      mkdir -p "$ROOT/cms/public/client/nitro/nitro-react"
      cp -r "$ROOT/client/nitro/nitro-react/dist" "$NITRO_DIST"
    fi

    NITRO_URL="http://localhost:8090"
    NITRO_WS_URL="ws://localhost:2096"
    NITRO_SUBPATH="/client/nitro/nitro-react/dist"

    if [ -d "$NITRO_DIST" ]; then
      if [ -f "$NITRO_DIST/renderer-config.json.example" ] && [ ! -f "$NITRO_DIST/renderer-config.json" ]; then
        cp "$NITRO_DIST/renderer-config.json.example" "$NITRO_DIST/renderer-config.json"
      fi
      if [ -f "$NITRO_DIST/ui-config.json.example" ] && [ ! -f "$NITRO_DIST/ui-config.json" ]; then
        cp "$NITRO_DIST/ui-config.json.example" "$NITRO_DIST/ui-config.json"
      fi

      if [ ! -f "$NITRO_DIST/.devenv-patched" ]; then
        echo "  → Corrigindo domínios e paths no cliente Nitro..."

        find "$NITRO_DIST" -maxdepth 1 -name "*.json" -exec sed -i \
          -e "s|wss://[a-zA-Z0-9._-]*:2096|$NITRO_WS_URL|g" \
          -e "s|https://[a-zA-Z0-9._-]*|$NITRO_URL|g" \
          {} \;

        if [ -f "$NITRO_DIST/renderer-config.json" ]; then
          sed -i "s|\"asset.url\": \"$NITRO_URL\"|\"asset.url\": \"$NITRO_URL/client/nitro/nitro-assets\"|" "$NITRO_DIST/renderer-config.json"
        fi

        if [ -f "$NITRO_DIST/index.html" ]; then
          sed -i \
            -e "s|src=\"/assets/|src=\"$NITRO_SUBPATH/assets/|g" \
            -e "s|href=\"/assets/|href=\"$NITRO_SUBPATH/assets/|g" \
            -e "s|href=\"/src/assets/index.css\"|href=\"$NITRO_SUBPATH/src/assets/index.css\"|" \
            -e "s|'/renderer-config.json'|'$NITRO_SUBPATH/renderer-config.json'|" \
            -e "s|'/ui-config.json'|'$NITRO_SUBPATH/ui-config.json'|" \
            "$NITRO_DIST/index.html"
        fi

        find "$NITRO_DIST" -name "*.css" -exec sed -i \
          -e "s|url(/src/assets/|url(./src/assets/|g" \
          -e "s|url(./src/assets/Ubuntu|url(./Ubuntu|g" \
          {} \;

        touch "$NITRO_DIST/.devenv-patched"
        echo "  ✓ Cliente Nitro corrigido e pronto"
      fi
    fi

    if command -v mysql &> /dev/null; then
      if mysql -h 127.0.0.1 -u root habbo -e "SELECT 1;" &> /dev/null; then
        HAS_SETTINGS=$(mysql -h 127.0.0.1 -u root habbo -sse "SHOW TABLES LIKE 'emulator_settings';" 2>/dev/null)
        if [ "$HAS_SETTINGS" = "emulator_settings" ]; then
          mysql -h 127.0.0.1 -u root habbo -e "UPDATE emulator_settings SET value='$NITRO_URL' WHERE \`key\`='websockets.whitelist';" 2>/dev/null
        fi
        HAS_WEBSITE_SETTINGS=$(mysql -h 127.0.0.1 -u root habbo -sse "SHOW TABLES LIKE 'website_settings';" 2>/dev/null)
        if [ "$HAS_WEBSITE_SETTINGS" = "website_settings" ]; then
          mysql -h 127.0.0.1 -u root habbo -e "UPDATE website_settings SET value='$NITRO_SUBPATH' WHERE \`key\`='nitro_path';" 2>/dev/null
        fi
      fi
    fi

    echo ""
    echo "✅ Setup verificado. Rode 'devenv up' para subir todos os serviços."
    echo "   CMS: $NITRO_URL  |  Jogo (via CMS): $NITRO_URL/game/nitro  |  WebSocket: $NITRO_WS_URL"
    echo ""
    set -e
  '';

  scripts.arcturus-reset-config.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    echo "[reset] config.ini removido — será recriado na próxima entrada do shell."
  '';

  scripts.arcturus-reset-db.exec = ''
    echo "[reset] Isso apaga TODO o estado do MySQL do devenv."
    read -p "Confirma? (digite 'sim'): " confirm
    if [ "$confirm" = "sim" ]; then
      rm -rf "${config.env.DEVENV_ROOT}/.devenv/state/mysql"
      echo "[reset] Estado apagado. Rode 'devenv up' para recriar com o schema importado."
    fi
  '';

  scripts.arcturus-reset-nitro.exec = ''
    rm -rf "${config.env.DEVENV_ROOT}/cms/public/client/nitro/nitro-react/dist"
    rm -rf "${config.env.DEVENV_ROOT}/client/nitro/nitro-react/dist"
    echo "[reset] Build do Nitro removido — será refeito na próxima entrada do shell."
  '';

  scripts.arcturus-full-reset.exec = ''
    rm -f "${config.env.DEVENV_ROOT}/arcturus/config.ini"
    rm -rf "${config.env.DEVENV_ROOT}/.devenv/state/mysql"
    rm -rf "${config.env.DEVENV_ROOT}/cms/public/client/nitro/nitro-react/dist"
    rm -rf "${config.env.DEVENV_ROOT}/client/nitro/nitro-react/dist"
    echo "[reset] Tudo resetado. Rode 'devenv up' para recriar do zero."
  '';

  processes.arcturus = {
    exec = ''
      JAR=$(find "${config.env.DEVENV_ROOT}/arcturus/target" -iname "*-jar-with-dependencies.jar" | head -1)
      cd "${config.env.DEVENV_ROOT}/arcturus" && java -jar "$JAR"
    '';
    process-compose.depends_on.mysql.condition = "process_healthy";
  };
}
