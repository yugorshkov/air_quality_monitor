provider "twc" {
  token = var.timeweb_token
}

data "twc_configurator" "server-config" {
  location = "ru-1"
}

data "twc_software" "docker" {
  name = "Docker"

  os {
    name = "ubuntu"
    version = "22.04"
  }
}

data "twc_ssh_keys" "twc-ssh" {
  name = "tw_terraform_key"
}

resource "twc_server" "aqm" {
  name = "aqm"
  os_id = data.twc_software.docker.os[0].id
  software_id = data.twc_software.docker.id

  configuration {
    configurator_id = data.twc_configurator.server-config.id
    disk = 1024 * 10
    cpu = 1
    ram = 1024 * 2
  }
  local_network {
    id = twc_vpc.network.id
  }
  ssh_keys_ids = [ data.twc_ssh_keys.twc-ssh.id ]
  depends_on = [ twc_vpc.network ]
}