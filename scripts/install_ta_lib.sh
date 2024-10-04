git clone https://github.com/JackZhao516/ta-lib-0.4.0-src
cd ta-lib-0.4.0-src
chmod +x configure
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib-0.4.0-src