FROM archlinux:base-devel

RUN groupadd -g 1001 -r builder && \
    useradd -m --no-log-init -r -u 1001 -g builder -G wheel builder && \
    sed --in-place 's/^#\s*\(%wheel\s\+ALL=(ALL:ALL)\s\+NOPASSWD:\s\+ALL\)/\1/' /etc/sudoers

COPY makepkg.conf /etc/makepkg.conf
COPY pacman.conf /etc/pacman.conf

RUN pacman -Syu --noconfirm --needed python python-pip pacman-contrib git wget && \
    pacman --noconfirm -Sc 

RUN pacman-key --init && pacman-key --populate && \
    git config --system --add safe.directory "*"

COPY --chown=builder:builder requirements.txt /aurei/requirements.txt

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN chown -R builder:builder $VIRTUAL_ENV

USER builder

WORKDIR /aurei

RUN pip install pkgconfig --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=builder:builder builder /aurei/builder
COPY --chown=builder:builder templates /aurei/templates
COPY --chown=builder:builder build.py /aurei/entrypoint.py

ENTRYPOINT ["python", "/aurei/entrypoint.py"]
