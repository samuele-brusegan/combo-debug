# =============================================================================
# Container 1: ROS 2 Humble + backend FastAPI + nodi demo.
#
# Il backend deve risiedere insieme a ROS per condividere il grafo e poter
# eseguire le SysCall alla CLI `ros2`.
# =============================================================================
FROM ros:humble-ros-base

# Evita prompt interattivi durante apt.
ENV DEBIAN_FRONTEND=noninteractive

# Pacchetti ROS necessari ai nodi demo e ai comandi diagnostici usati dal
# backend (ros2 node/topic fanno parte di ros2cli, gia' presente in ros-base;
# std_msgs serve ai nodi di esempio).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-pip \
        ros-humble-std-msgs \
        ros-humble-rmw-fastrtps-cpp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dipendenze Python del backend (layer separato per sfruttare la cache).
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/backend/requirements.txt

# Codice applicativo: backend + nodi ROS 2 demo.
COPY backend /app/backend
COPY ros2_demo /app/ros2_demo

# Il package dell'app e' importabile come `app` (uvicorn app.main:app).
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

RUN chmod +x /app/backend/entrypoint.sh /app/ros2_demo/run_demo.sh

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
