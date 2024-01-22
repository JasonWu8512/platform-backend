#!/usr/bin/expect -f
# 同步数据操作只需要一步命令
set timeout 5
# 初始化变量
# set ip_host [lindex $argv 0]

# expect {
#         "yes/no" { send "yes\r";exp_continue }
#         "password:" { send "$passwd\r" }
# }


proc do_console_login {passwd} {
        set timeout 5
        set done 2
        set timeout_case 0

        while ($done) {
                expect {
                        "*yes/no*" { send "yes\r" }
                        "*password*" { send "$passwd\r" }
                        "*Jumpserver*" {
                                set done 0
                                send "p\r"
                        }
                         timeout {
                                 switch -- $timeout_case {
                                         0 { send "n\r" }
                                         1 {
                                                 send_user "Send a return...n\r"
                                                 send "p\r"
                                         }
                                         2 {
                                                 puts stderr "Login time out...n\r"
                                                 exit 1
                                         }
                                 }
                                 incr timeout_case
                         }
                }
                if {$done == 0} break
        }

}


proc do_exec_cmd {server_ip cmd_line} {

	send "p\r"
	sleep 1
	send "$server_ip\r"
#    set timeout 2
    # puts "Connect Success & $server_ip\r"
    expect "*deploy@$server_ip*"
    sleep 2
    set lins "$cmd_line >> anc.txt"
    send "$lins\r"
    puts "Execute Success & $lins \r"
    sleep 2
   send "exit\r"
#    sleep 2
	  send "q\r"
}



proc do_exec_cmd_while {server_ip cmd_line} {
# 	send "p\r"
# 	sleep 1
# 	send "$server_ip\r"
# #    set timeout 2
#     # puts "Connect Success & $server_ip\r"
#     expect "*deploy@$server_ip*"
#     sleep 2
#     set lins "$cmd_line >> anc.txt"
#     send "$lins\r"
#     puts "Execute Success & $lins \r"
#     sleep 2
#    send "exit\r"
# #    sleep 2
# 	  send "q\r"
	set timeout 30
    set done 2
    set timeout_case 0
	set isdone 1
	set runline "$cmd_line >> /home/deploy/sync_data.log"
	  while ($isdone) {
                expect {
                        # "*deploy*" { send "sd\r" }
                        # "*Opt*" { send "server_ip\r" }
                        "*deploy*" {
                          sleep 1
                        	send "$runline\r"
                        	sleep 10
                        	set isdone 4

                        }
                        "*Opt*" {
                          sleep 1
                          send "$server_ip\r"
                          sleep 3
                        }
                        # "*Jumpserver*" {
                        #         set done 0
                        #         send "p\r"
                        # }
                         timeout {
                                 switch -- $timeout_case {
                                         0 { send "n\r" }
                                         1 {
                                                 send_user "Send a return...n\r"
                                                 send "p\r"
                                         }
                                         2 {
                                                 puts stderr "Login time out...n\r"
                                                 exit 1
                                         }
                                 }
                                 incr timeout_case
                         }
                }
                if { $isdone == 4 } break
                incr isdone
                # if ( $isdone == 3 ) {  }
#                puts "$isdone = isdone"
#                puts "$runline"
                sleep 2
        }
	send "exit\r"
	sleep 1
	send "q\r"
}


set i 1
set cmd_line ""
while {$i<"$argc"} {
  set param [lindex $argv $i]
  set commbak "$cmd_line $param"
  set cmd_line $commbak
  incr i
}

# if {$argc<2} {
#         puts stderr "Usage: $argv0 login passwaord.n "
#         exit 1
# }

# set LOGIN   "[lindex $argv 0]"
set PASS    "demon_jiao"
set server_ip [lindex $argv 0]

spawn ssh demon_jiao@jumpserver.jiliguala.com -p 2222

puts "Connect $server_ip, exec $cmd_line"

do_console_login $PASS
# do_exec_cmd $server_ip $cmd_line
do_exec_cmd_while $server_ip $cmd_line

send "exit\r"
	sleep 1
	send "q\r"

close
exit 0

