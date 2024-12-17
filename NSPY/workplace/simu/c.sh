
c++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) ../C/dleft/Sketches_dleft.cpp -o ../C/dleft/Sketches$(python3-config --extension-suffix)
c++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) ../C/sumax/Sketches_sumax.cpp -o ../C/sumax/Sketches$(python3-config --extension-suffix)
c++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) ../C/marple/Sketches_marple.cpp -o ../C/marple/Sketches$(python3-config --extension-suffix)
c++ -O3 -Wall -shared -std=c++11 -fPIC $(python3 -m pybind11 --includes) ../C/netseer/Netseer.cpp -o ../C/netseer/Netseer$(python3-config --extension-suffix)


