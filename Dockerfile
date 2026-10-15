FROM debian:12.15-slim

# fork: librime-lua is back in the plugin set (see the note in commit-ci.yml for
# the Boost side). It takes Lua from the distro here rather than from its
# in-tree thirdparty/lua5.4, because install-plugins.sh does not run a plugin's
# own action-install script -- which makes this the only graph that exercises
# the plugin's find_package(PkgConfig) Lua branch. octagram, charcode and
# predict stay; charcode is the one plugin that really needs Boost (boost::locale),
# so libboost-locale-dev remains, and libboost-regex-dev remains because this
# graph is the real-Boost datapoint: the plugin shim is applied whether or not
# /usr/include/boost exists, so the image proves the override works.
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  git \
  build-essential \
  cmake \
  ninja-build \
  pkg-config \
  libboost-dev \
  libboost-regex-dev \
  libboost-locale-dev \
  libgoogle-glog-dev \
  libgtest-dev \
  liblua5.4-dev \
  libyaml-cpp-dev \
  libleveldb-dev \
  libmarisa-dev \
  libopencc-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /librime
COPY . .

RUN bash install-plugins.sh \
  hchunhui/librime-lua \
  rime/librime-charcode \
  lotem/librime-octagram \
  rime/librime-predict

RUN cmake -B build -G Ninja \
  -DCMAKE_BUILD_TYPE:STRING=Release \
  -DENABLE_LOGGING:BOOL=ON \
  -DBUILD_TEST:BOOL=ON \
  -DBUILD_STATIC:BOOL=OFF \
  -DBUILD_SHARED_LIBS:BOOL=ON
RUN cmake --build build

RUN ctest --test-dir build --output-on-failure
