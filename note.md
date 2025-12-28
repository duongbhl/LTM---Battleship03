```
// Vi client sua kha nhieu nen note vao day cho ae nam duoc

// Phan local nay chua tung merge voi main nen co the khac chut, ko lien quan toi ket noi hien tai cua main

//Phan local nay van dung ket noi 127.0.0.1

1. Chuyen het ket noi cua client cho network_client.py
network_client.py boc lai 1 socket duy nhat de gui.py va online_battleship_gui.py dung chung socket do, thay vi hien tai online_battleship_gui.py phai mo 1 socket moi de tim tran

network_client.py:
- them ham from_socket de boc socket duoc tao ban dau de tai su dung

gui.py:
- them bien session_sock vao global
- sua lai cau truc bien cua run_online_game thanh run_online_game(session_sock, current_user, mode) 
- sua them 1 vai cho de phu hop voi network_client.py

online_battleship_gui.py:
- sua lai cau truc bien trong ham run_online_game nhu gui.py
- sua lai 1 doan gui message toi server de phu hop voi cau truc bien moi (hoac trong gui.py ko nho ro lam)

2. Sua lai online_battleship_gui.py de fix bug:
- Xoa cmd LOGIN_OK va LOGIN_FAIL do hien tai file nay ko xu ly nua
- Chuyen toan bo FIND_MATCH len dau ham run_online_game
- xoa bien sent_find do ko dung nua