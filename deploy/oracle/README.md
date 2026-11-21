# Déploiement RetailPulse sur Oracle Cloud

Cette configuration héberge Streamlit et PostgreSQL 17 sur la même VM OCI.
PostgreSQL utilise un volume persistant et n'a aucun port publié sur Internet.
Le dashboard redémarre automatiquement et se connecte avec le rôle
`retailpulse_reader`.

## 1. Créer la VM OCI

Dans la Console OCI, créez une VM Ubuntu 24.04 LTS avec une IPv4 publique et
une clé SSH. Conservez la clé privée sur votre PC et ne la transmettez pas.
Si vous utilisez une offre Always Free, vérifiez l'étiquette Always Free et
les quotas dans la Console avant de créer la VM ; la capacité peut varier
selon la région.

Dans la VCN / liste de sécurité ou le Network Security Group, autorisez :

- TCP 22 depuis **votre adresse IP** pour SSH.
- TCP 8501 depuis `0.0.0.0/0` pour le dashboard public.
- N'ajoutez pas de règle publique pour PostgreSQL (5432).

Une VM OCI doit avoir une IP publique et un chemin réseau autorisé pour être
joignable depuis Internet. Si le pare-feu Ubuntu `ufw` est actif, autorisez
aussi le port 8501 :

```bash
sudo ufw allow 8501/tcp
```

## 2. Installer Docker et copier les fichiers

Installez Docker Engine avec son plugin Compose en suivant la procédure
officielle pour Ubuntu : <https://docs.docker.com/engine/install/ubuntu/>.
Vérifiez `docker compose version`.

Sur votre PC, créez le paquet source sans données ni secrets :

```powershell
& .\.venv\Scripts\python.exe .\scripts\package_oracle_deploy.py
```

Copiez `dist\retailpulse-oracle-deploy.zip` et le dump de la base vers la VM
avec SCP (remplacez le nom de clé et l'adresse IP par les vôtres) :

```powershell
scp -i "$env:USERPROFILE\.ssh\oracle_vm.key" .\dist\retailpulse-oracle-deploy.zip ubuntu@IP_PUBLIQUE:/home/ubuntu/
scp -i "$env:USERPROFILE\.ssh\oracle_vm.key" .\retailpulse_gold.dump ubuntu@IP_PUBLIQUE:/home/ubuntu/
```

Sur la VM :

```bash
cd /home/ubuntu
unzip retailpulse-oracle-deploy.zip
cd RetailPulse/deploy/oracle
cp .env.example .env
nano .env
```

Dans `.env`, définissez deux secrets longs et différents pour
`POSTGRES_PASSWORD` et `DASHBOARD_DB_PASSWORD`. Ne copiez pas le `.env` local
de votre PC et ne placez aucun mot de passe dans le paquet source.
Vous pouvez générer chaque valeur avec `openssl rand -hex 32` sur la VM, puis
les saisir dans l'éditeur sans les envoyer dans le chat.

## 3. Migrer les tables Gold

Sur votre PC Windows, exportez uniquement le schéma Gold PostgreSQL existant.
La commande demande le mot de passe de l'administrateur PostgreSQL local :

```powershell
pg_dump -h localhost -p 5432 -U postgres -d RetailPulse --schema=gold --format=custom --no-owner --no-acl --file=retailpulse_gold.dump
```

Si PostgreSQL local utilise une autre base ou un autre port, adaptez ces
paramètres. Transférez ce dump à la VM avec SCP comme indiqué plus haut.

Sur la VM, initialisez PostgreSQL, restaurez Gold, puis accordez au dashboard
uniquement les droits de lecture :

```bash
sudo docker compose up -d postgres
sudo docker compose cp /home/ubuntu/retailpulse_gold.dump postgres:/tmp/retailpulse_gold.dump
sudo docker compose exec -T postgres pg_restore -U retailpulse_admin -d retailpulse --no-owner --no-acl --exit-on-error /tmp/retailpulse_gold.dump
sudo docker compose exec -T postgres psql -U retailpulse_admin -d retailpulse -v ON_ERROR_STOP=1 < grant_reader.sql
```

Le rôle `retailpulse_reader` est créé au premier démarrage du volume. Le dump
ne contient pas les secrets ni les rôles du serveur source.

## 4. Construire et lancer le dashboard

```bash
sudo docker compose up -d --build dashboard
sudo docker compose ps
sudo docker compose logs --tail=100 dashboard
```

Ouvrez ensuite `http://IP_PUBLIQUE:8501`. La règle de redémarrage Docker
maintient les conteneurs actifs après un redémarrage de la VM. Le lien local
`192.168.129.78:8501` restera propre à votre réseau et sera remplacé par
l'adresse publique de la VM.

Cette première URL utilise HTTP. Pour un domaine avec HTTPS, ajoutez un nom
DNS pointant vers l'IP publique et placez un reverse proxy TLS devant le
dashboard. L'application présente le jeu de données public ; les identifiants
PostgreSQL restent côté serveur et ne sont jamais envoyés au navigateur.
