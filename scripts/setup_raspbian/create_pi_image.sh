#!/bin/bash

# TODO:
# Add error detection
# exit if something goes wrong

RASPBIANDATE="2017-04-10"
FINALIMAGE="territorios-raspbian"
SETUPSCRIPT="setup_pi.sh"

MOUNTPOINT="mnt"
CACHEDIR="cache"
DISTDIR="dist"

QEMUBIN="qemu-arm"

RASPBIANFILE="${RASPBIANDATE}-raspbian-jessie-lite"
RASPBIANURL="https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-${RASPBIANDATE}/${RASPBIANFILE}.zip"

if [ ! -d "$CACHEDIR" ]; then
  mkdir "$CACHEDIR"
fi

if [ ! -e "$CACHEDIR"/${RASPBIANFILE}.zip ]; then
  wget -O ${CACHEDIR}/${RASPBIANFILE}.zip $RASPBIANURL
fi

if [ ! -e ${CACHEDIR}/zero.img ]; then
  dd if=/dev/zero of=${CACHEDIR}/zero.img bs=1M count=1000
fi

if [ ! -e "$CACHEDIR"/${RASPBIANFILE}.img ]; then
  unzip -d ${CACHEDIR} ${CACHEDIR}/${RASPBIANFILE}.zip
  # Resize image and filesystem
  cat ${CACHEDIR}/zero.img >> ${CACHEDIR}/${RASPBIANFILE}.img
fi

NEWSIZE=$(sudo parted -m ${CACHEDIR}/${RASPBIANFILE}.img p | grep "${RASPBIANFILE}.img" | cut -d ':' -f2)
sudo parted -s ${CACHEDIR}/${RASPBIANFILE}.img resizepart 2 $NEWSIZE

sudo kpartx -a ${CACHEDIR}/${RASPBIANFILE}.img
LOOPPART=$(sudo losetup -l -n -O NAME,BACK-FILE | grep ${CACHEDIR}/${RASPBIANFILE}.img | sed 's/.*\(loop[0-9]\).*/\/dev\/mapper\/\1p2/')

sudo fsck.ext4 -f $LOOPPART
sudo resize2fs $LOOPPART

sudo mount $LOOPPART $MOUNTPOINT
for i in /proc /dev /tmp /dev/pts /sys; do
  sudo mount -o bind ${i} ${MOUNTPOINT}/${i}
done

if [ -e ${CACHEDIR}/debs.tar ]; then
  sudo tar xf ${CACHEDIR}/debs.tar -C ${MOUNTPOINT}/var/cache/apt/archives
fi

sudo cp ${SETUPSCRIPT} ${MOUNTPOINT}


# Exec script
sudo cp /usr/bin/${QEMUBIN} ${MOUNTPOINT}/usr/bin/
# Create dpkg_diversion
cat <<EOF | sudo tee ${MOUNTPOINT}/dpkgdivert >/dev/null
#!/bin/sh
dpkg-divert --add --local \
        --divert /usr/sbin/invoke-rc.d.chroot \
        --rename /usr/sbin/invoke-rc.d
cp /bin/true /usr/sbin/invoke-rc.d
echo -e "#!/bin/sh\nexit 101" > /usr/sbin/policy-rc.d
chmod +x /usr/sbin/policy-rc.d
EOF

sudo chmod +x ${MOUNTPOINT}/dpkgdivert
sudo chroot ${MOUNTPOINT} /dpkgdivert

sudo chroot ${MOUNTPOINT} /bin/bash ${SETUPSCRIPT}


# Unmount image
# Remove dpkg_diversion
cat <<EOF | sudo tee ${MOUNTPOINT}/dpkgdivert >/dev/null
#!/bin/sh
rm -f /usr/sbin/policy-rc.d
rm -f /usr/sbin/invoke-rc.d
dpkg-divert --remove --rename /usr/sbin/invoke-rc.d
EOF

sudo chmod +x ${MOUNTPOINT}/dpkgdivert
sudo chroot ${MOUNTPOINT} /dpkgdivert
sudo rm -v ${MOUNTPOINT}/{dpkgdivert,${SETUPSCRIPT},usr/bin/${QEMUBIN}}

QEMUPIDS=`ps ax | grep ${QEMUBIN} | cut -d ' ' -f1 | grep -v "^$"`
for i in $QEMUPIDS; do
  sudo kill $i
done
for i in proc dev/pts tmp dev sys ; do
  sudo umount ${MOUNTPOINT}/${i}
done
sudo umount ${MOUNTPOINT}
sudo kpartx -d ${CACHEDIR}/${RASPBIANFILE}.img


if [ ! -d "$DISTDIR" ]; then
  mkdir "$DISTDIR"
fi
cat ${CACHEDIR}/${RASPBIANFILE}.img | gzip > ${DISTDIR}/${FINALIMAGE}.img.gz
