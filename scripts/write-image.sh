#!/bin/sh

# Spreedbox write SD card image tool
# Niels Mache, struktur AG

bdev=
img=
tmpimg=
size=0
failures=0
ndevs=

# write and compare image
write_img()
{
  img=$1
  bdev=$2
  sbytes=$3

  echo "Writing Spreedbox image $img to $bdev (size $size MB)"

  if [ "$ndevs" = "1" ]; then
      pv $img | dd of=$bdev bs=1M conv=sync,fdatasync iflag=fullblock 2> /dev/null
  else
      dd if=$img of=$bdev bs=1M conv=sync,fdatasync iflag=fullblock 2> /dev/null
  fi
  if [ $? != 0 ]; then
      echo "Writing image file $img to block device $bdev failed. Exiting."
      return 1
  fi

  # Comparing data $bdev
  if [ "$ndevs" = "1" ]; then
      echo "Validating Spreedbox image $img on $bdev ..."
      dd if=$bdev bs=1M count=$size 2> /dev/null | pv -s $sbytes | cmp - $img 2> /dev/null
  else
      dd if=$bdev bs=1M count=$size 2> /dev/null | cmp - $img 2> /dev/null
  fi
  if [ $? != 0 ]; then
    echo "ERROR: Written image file $image differs on block device $bdev. Exiting."
    return 1
  else
    echo "WRITTEN and VERIFIED image $img on block device $bdev."
    return 0
  fi
}




# Main program

if [ $# -lt 2 -o $# -gt 5 ]; then
    echo "Usage: $0 <image file> <block device> [<block device>]"
    echo "Maximum no. of 4 block devices."
    exit 1
fi
if [ ! -f $1 ]; then
    echo "$img not found. Exiting."
    exit 1
fi

img=$1
shift
i=0
for dev in $*; do
  if [ ! -b $dev ]; then
      echo "$dev is not a block device. Exiting."
      exit 1
  fi
  let i++
  bdev[$i]=$dev
  #echo "D: ${bdev[$i]}"
done

ndevs=$i

# calc size in Mbytes
# extend image to Mbyte border if required
s=`stat -c "%s" $img`
size=$[$s / 1024 / 1024]
sbytes=$[$size * 1024 * 1024]

if [ $sbytes != $s ]; then
  echo "Image file $img requires padding to full MByte."
  imgnew=$img-padded1MB
  if [ ! -e $imgnew ]; then
    cp -p $img $imgnew
  else
    echo "Padded file $imgnew exists. Exiting."
    exit 1
  fi
  # increment block count
  size=$[size+1]

  dd if=/dev/null of=$imgnew bs=1M count=0 seek=$size 2> /dev/null
  if [ $? != 0 ]; then
    echo "Padding image file $imagenew failed. Exiting."
    exit 1
  else
    echo "Image file $img zero-padded to $size MB, new image $imgnew written."
    img=$imgnew
    # uncomment if padded file should be written now
    echo "Exiting."
    exit 1
  fi
fi

# writing image in parallel
for (( i=1; i <= $ndevs; i++ )); do
  write_img $img ${bdev[$i]} $sbytes &
done
# wait for completion
for job in `jobs -p`; do
  wait $job || let failures++
done
# check for errors
if [ $failures -eq 0 ]; then
  echo "Image successfully written to $ndevs block devices."
  exit 0
else
  echo "ERROR writing image ($failures errors)."
  exit 1
fi
