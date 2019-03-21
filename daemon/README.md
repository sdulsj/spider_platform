# 守护进程
使用supervisor进行进程守护，适用版本Python2.7

***********************************************
### 安装配置supervisor
```
# 安装
wget --no-check-certificate https://bootstrap.pypa.io/ez_setup.py -O - | sudo python
easy_install supervisor
easy_install-2.7 supervisor

# 配置
mkdir /etc/supervisor
mkdir /etc/supervisor/conf.d
echo_supervisord_conf > /etc/supervisor/supervisord.conf
# supervisor的配置示例，注：分号（;）开头的配置表示注释

# 配置systemctl服务
cd /lib/systemd/system
# 创建supervisor.service文件，修改文件权限为766
chmod 766 supervisor.service
sed -i 's/\r$//' supervisor.service
# 设置开机启动
systemctl enable supervisor.service
systemctl daemon-reload
#systemctl is-enabled xxx.service #查询服务是否开机启动
#systemctl enable xxx.service #开机运行服务
#systemctl disable xxx.service #取消开机运行
#systemctl start xxx.service #启动服务
#systemctl stop xxx.service #停止服务
#systemctl restart xxx.service #重启服务
#systemctl reload xxx.service #重新加载服务配置文件
#systemctl status xxx.service #查询服务运行状态
#systemctl --failed #显示启动失败的服务

# 配置service服务
cd /etc/rc.d/init.d/
# 创建supervisor脚本文件，修改文件权限为755，设置开机启动
chmod 755 /etc/rc.d/init.d/supervisor
chkconfig supervisor on

supervisorctl help # 查看帮助
supervisorctl reload # 修改完配置文件后重新启动supervisor
supervisorctl status # 查看supervisor监管的进程状态
supervisorctl start 进程名 # 启动XXX进程
supervisorctl stop 进程名 # 停止XXX进程
supervisorctl restart 进程名 # 重启XXX进程
supervisorctl tail -f 进程名 # 查看XXX进程的日志
supervisorctl stop all # 停止全部进程，注：start、restart、stop都不会载入最新的配置文件
supervisorctl reread # 读取有更新（增加）的配置文件，不会启动新添加的程序
supervisorctl update # 根据最新的配置文件，启动新配置或有改动的进程，配置没有改动的进程不会受影响而重启
supervisorctl shutdown # 关闭supervisor
```
***********************************************
### 安装配置nginx
```
# 安装依赖
yum install gcc-c++ pcre pcre-devel zlib zlib-devel openssl openssl-devel -y

# 检查卸载
find -name nginx
yum remove nginx

# yum安装
yum install nginx
# 或下载安装 
wget http://nginx.org/download/nginx-1.14.0.tar.gz
tar -zxvf nginx-1.14.0.tar.gz
cd  nginx-1.14.0
./configure --prefix=/usr/nginx
make
make install
whereis nginx

# 操作
cd /usr/nginx/sbin/
./nginx
./nginx -s stop  # 此方式相当于先查出nginx进程id再使用kill命令强制杀掉进程
./nginx -s quit  # 此方式停止步骤是待nginx进程处理任务完毕进行停止
./nginx -s reload  # 重新加载配置文件
./nginx -t  # 测试配置文件是否正常

# 查询
ps aux|grep nginx

# 防火墙设置，若未开启，则跳过此步
firewall-cmd --permanent --zone=public --add-service=http
firewall-cmd --permanent --zone=public --add-service=https
firewall-cmd --reload

# 开机启动
systemctl enable nginx
```
***********************************************
### 安装配置keepalived
```
# 安装
yum install -y keepalived
# 启动
systemctl start keepalived
```