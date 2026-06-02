CREATE ROLE ccwbot_ops_reader LOGIN PASSWORD '<set manually>';
GRANT CONNECT ON DATABASE ccwbot TO ccwbot_ops_reader;
GRANT USAGE ON SCHEMA public TO ccwbot_ops_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ccwbot_ops_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE ccwbot IN SCHEMA public
GRANT SELECT ON TABLES TO ccwbot_ops_reader;

