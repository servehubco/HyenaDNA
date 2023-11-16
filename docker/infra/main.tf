

provider "aws" {
  region = "eu-west-1"  # Change this to your preferred AWS region
}


resource "aws_key_pair" "deployer" {
  key_name   = "deployer-key"
  public_key = file("~/.ssh/id_rsa.pub")  # Path to your SSH public key
}

resource "aws_security_group" "allow_ssh" {
  name        = "allow_ssh"
  description = "Allow SSH inbound traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Warning: This allows SSH from anywhere. Narrow this down for security.
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"           # This represents all protocols.
    cidr_blocks = ["0.0.0.0/0"]  # This allows all outbound traffic.
  }
}

resource "aws_instance" "example" {
  ami           = "ami-0a074b0a311a837ac"  # Example AMI for Amazon Linux 2 in us-west-2 region. Update if necessary.
  instance_type = "g4dn.xlarge"  # Change this to your preferred instance type
  key_name      = aws_key_pair.deployer.key_name

  vpc_security_group_ids = [aws_security_group.allow_ssh.id]

  tags = {
    Name = "terraform-example-instance"
  }

  root_block_device {
    volume_size = 200 # in GB <<----- I increased this!
    volume_type = "gp3"
  }

#  provisioner "remote-exec" {
#    inline = [
#      "adduser sammy",
#      "usermod -aG docker sammy"
#    ]
#
#    connection {
#      type        = "ssh"
#      user        = "ubuntu"
#      private_key = file("~/.ssh/id_rsa")
#      host        = self.public_ip
#    }
#  }
}

output "instance_public_ip" {
  description = "The public IP of the EC2 instance"
  value       = aws_instance.example.public_ip
}