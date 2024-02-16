resource "twc_vpc" "network" {
  name = "network-1"
  subnet_v4 = "192.168.0.0/24"
  location = "ru-1"
}

data "twc_database_preset" "db-preset" {
  location = "ru-1"
  type = "postgres"
  disk = 1024 * 8
  
  price_filter {
    from = 100
    to = 200
  }
}

resource "twc_database_cluster" "pg-cluster" {
  name = "aqm_prod"
  type = "postgres14"
  preset_id = data.twc_database_preset.db-preset.id
  network {
    id = twc_vpc.network.id
  }
  depends_on = [ twc_vpc.network ]
}

resource "twc_database_instance" "air_quality" {
  cluster_id = twc_database_cluster.pg-cluster.id
  name = "air_quality"
  depends_on = [ twc_database_cluster.pg-cluster ]
}

resource "twc_database_instance" "metabase" {
  cluster_id = twc_database_cluster.pg-cluster.id
  name = "metabase"
  depends_on = [ twc_database_cluster.pg-cluster ]
}

resource "twc_database_user" "pg-user" {
  cluster_id = twc_database_cluster.pg-cluster.id
  login = var.db_user
  password = var.db_pass
  privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "REFERENCES", "CREATE", "DROP", "INDEX"]
  depends_on = [ twc_database_cluster.pg-cluster ]
}