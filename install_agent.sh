echo "Создание каталога для настроек агента"
mkdir -p /etc/DockerNetAgent/
echo "[global]" > /etc/DockerNetAgent/agent.conf
read -p "Введите адрес сервера, на который будут отправляться метрики: " serverAddress
echo "server="$serverAddress >> /etc/DockerNetAgent/agent.conf
read -p "Введите токен для доступа к серверу: " serverToken
echo "token="$serverToken >> /etc/DockerNetAgent/agent.conf
read -p "Введите задержку между отправкой данных: " serverTimeout
echo "timeout="$serverTimeout >> /etc/DockerNetAgent/agent.conf
wget https://github.com/d0x47/D0xNetAgent/archive/master.zip
unzip master.zip
cp -R D0xNetAgent-master/docker-net-agent.sh /usr/bin/docker-net-agent.sh
cp -R D0xNetAgent-master/docker-net-agent.service /etc/systemd/system/docker-net-agent.service
rm -rf master.zip D0xNetAgent-master