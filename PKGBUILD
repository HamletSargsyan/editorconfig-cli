# Maintainer: Your Name <youremail@domain.com>
pkgname=editorconfig_cli
pkgver=0.0.0
pkgrel=1
pkgdesc="editorconfig cli"
arch=("x86_64")
url=""
license=('MIT')
depends=('python')
makedepends=('python-poetry')
source=("file://${PWD}/dist/${pkgname}-${pkgver}.tar.gz")
noextract=()
sha256sums=('SKIP')

prepare() {
    tar -xf "${srcdir}/${pkgname}-${pkgver}.tar.gz" -C "${srcdir}"
    cd "${srcdir}/${pkgname}-${pkgver}"
    poetry install --no-root
}

build() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    poetry build
}

package() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    export PYTHONPATH="${srcdir}/${pkgname}-${pkgver}"
    install -Dm755 "$(poetry run which editorconfig-cli)" "${pkgdir}/usr/bin/editorconfig-cli"
}
