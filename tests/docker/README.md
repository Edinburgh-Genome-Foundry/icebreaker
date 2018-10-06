# Docker configuration for icebreaker tests

# Steps to build the initial database:

This can be useful when the current backup doesnt want to work:

- Start from a fresh ICE instance with clean postgres volume
- ``docker-compose up`` 
- login in on ``localhost:9999`` with Administrator/Administrator
- create user John Doe with email/password john/john and description "I am John"
- Sign in as john/john
- create an API key with name "johnbot" and copy it in ``configs/john_doe_token.yml`` in this repo
- Create two parts Test1 and Test2
- Create a folder called "test_folder"