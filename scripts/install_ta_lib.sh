sudo apt-get update
sudo apt-get install -y build-essential wget git cmake
git clone  https://github.com/ta-lib/ta-lib.git ta-lib
cd ta-lib
chmod +x install uninstall
sudo ./uninstall --prefix /usr
sudo ./install --prefix /usr
cd ..
rm -rf ta-lib
