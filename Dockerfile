FROM archlinux:base-devel

RUN pacman -Syu --noconfirm python python-pip pacman-contrib git wget

RUN groupadd -g 1001 -r builder && useradd -m --no-log-init -r -u 1001 -g builder -G wheel builder
RUN sudo sed --in-place 's/^#\s*\(%wheel\s\+ALL=(ALL)\s\+NOPASSWD:\s\+ALL\)/\1/' /etc/sudoers

COPY makepkg.conf /etc/makepkg.conf

COPY requirements.txt /requirements.txt
COPY build.py /entrypoint.py

RUN pip install -r requirements.txt

USER builder

ENTRYPOINT ["/entrypoint.py"]
