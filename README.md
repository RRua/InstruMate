# InstruMate
ForensicMate - Static Analysis Module


### Installation

wget https://www.python.org/ftp/python/3.10.15/Python-3.10.15.tgz

tar -xvzf Python-3.10.15.tgz


./configure \
    --prefix=/opt/python/python-310 \
    --enable-shared \
    --enable-optimizations \
    --enable-ipv6 \
    LDFLAGS=-Wl,-rpath=/opt/python/python-310/lib,--disable-new-dtags
    
make
make install

switch to dev user
/opt/python/python-310/bin/python3 -m venv venv

./venv/bin/pip install -r requirements.txt


download jdk 8 and jdk 17
mkdir /opt/java

vim /etc/profile
export JAVA_HOME="/opt/java/jdk1.8.0_202"
export PATH=$JAVA_HOME/bin:$PATH

update-alternatives --list java
update-alternatives --set java <path-jdk-8/bin/java>
update-alternatives --set javac <path-jdk-8/bin/javac>
update-alternatives --set java <path-jdk-17/bin/java>
update-alternatives --set javac <path-jdk-17/bin/javac>

update-alternatives --config java
update-alternatives --config javac

.bashrc
export PATH="/home/leandro/Android/Sdk/emulator/:$PATH"
