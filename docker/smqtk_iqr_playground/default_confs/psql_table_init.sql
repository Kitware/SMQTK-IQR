CREATE TABLE IF NOT EXISTS descriptors_resnet50_pool5 (
  uid       TEXT  NOT NULL,
  vector    BYTEA NOT NULL,

  PRIMARY KEY (uid)
);
CREATE TABLE IF NOT EXISTS descriptor_set_resnet50_pool5 (
  uid       TEXT  NOT NULL,
  element   BYTEA NOT NULL,

  PRIMARY KEY (uid)
);
