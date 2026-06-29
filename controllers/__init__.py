"""
Pacote controllers (vestigial / não utilizado nesta arquitetura).

A estrutura de diretorios original sugerida para este projeto incluia
um pacote `controllers/` separado. Na pratica, ao adotar o padrao
MVVM (ver `viewmodels/`), o papel que um "controller" exerceria -
orquestrar a comunicacao entre a View e a camada de Service - e
absorvido pelos proprios ViewModels:

    View  <-- Signals/Slots -->  ViewModel  -->  Service  -->  Repository

Cada ViewModel (`viewmodels/home_viewmodel.py`,
`viewmodels/patients_viewmodel.py`, etc.) ja cumpre integralmente essa
responsabilidade, tornando um pacote `controllers/` adicional
redundante. Este pacote foi mantido vazio (em vez de removido)
apenas para preservar a estrutura de diretorios original do
documento de especificacao, mas nenhum modulo do sistema importa
deste pacote.
"""
