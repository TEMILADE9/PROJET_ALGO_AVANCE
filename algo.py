import re
import sqlite3
from datetime import date


def connecter(nom_base="commandes.db"):
    conn = sqlite3.connect(nom_base)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def creer_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS DELEGUE (
        codedeleg TEXT PRIMARY KEY, nomdeleg TEXT NOT NULL,
        prenomdeleg TEXT, telephone TEXT, salaire REAL
    );
    CREATE TABLE IF NOT EXISTS CLIENT (
        codcli TEXT PRIMARY KEY, nomcli TEXT NOT NULL,
        prenomcli TEXT, sexecli TEXT, telcli TEXT, villecli TEXT
    );
    CREATE TABLE IF NOT EXISTS PRODUIT (
        refprod TEXT PRIMARY KEY, libprod TEXT NOT NULL, prixunit REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS COMMANDE (
        numcde TEXT PRIMARY KEY, datecde TEXT NOT NULL,
        codcli TEXT NOT NULL, codedeleg TEXT NOT NULL,
        FOREIGN KEY (codcli) REFERENCES CLIENT(codcli),
        FOREIGN KEY (codedeleg) REFERENCES DELEGUE(codedeleg)
    );
    CREATE TABLE IF NOT EXISTS COMMANDER (
        numcde TEXT NOT NULL, refprod TEXT NOT NULL, quantite INTEGER NOT NULL,
        PRIMARY KEY (numcde, refprod),
        FOREIGN KEY (numcde) REFERENCES COMMANDE(numcde) ON DELETE CASCADE,
        FOREIGN KEY (refprod) REFERENCES PRODUIT(refprod)
    );
    """)
    conn.commit()


FORMAT_CODCLI    = r"^C\d{3}$"
FORMAT_NUMCDE    = r"^CDE\d{3}$"
FORMAT_REFPROD   = r"^P\d{3}$"
FORMAT_CODEDELEG = r"^D\d{3}$"


def saisir_code(libelle, pattern, exemple):
    while True:
        valeur = input(f"{libelle} (format : {exemple}) : ").strip().upper()
        if re.match(pattern, valeur):
            return valeur
        print(f"  -> Format invalide. Exemple attendu : {exemple}")


def saisir_texte_non_vide(libelle):
    while True:
        valeur = input(f"{libelle} : ").strip()
        if valeur != "":
            return valeur
        print("  -> Ce champ ne peut pas etre vide.")


def saisir_sexe():
    while True:
        valeur = input("Sexe (M/F) : ").strip().upper()
        if valeur in ("M", "F"):
            return valeur
        print("  -> Valeur invalide. Le sexe doit etre M ou F uniquement.")


def saisir_telephone():
    while True:
        valeur = input("Telephone (8 chiffres) : ").strip()
        if valeur.isdigit() and len(valeur) == 8:
            return valeur
        print("  -> Telephone invalide. Il doit contenir exactement 8 chiffres.")


def saisir_entier_positif(libelle):
    while True:
        valeur = input(f"{libelle} : ").strip()
        if valeur.isdigit() and int(valeur) > 0:
            return int(valeur)
        print(f"  -> {libelle} invalide. Ce doit etre un entier strictement positif.")


def client_existe(conn, codcli):
    return conn.execute("SELECT 1 FROM CLIENT WHERE codcli = ?", (codcli,)).fetchone() is not None


def delegue_existe(conn, codedeleg):
    return conn.execute("SELECT 1 FROM DELEGUE WHERE codedeleg = ?", (codedeleg,)).fetchone() is not None


def produit_existe(conn, refprod):
    return conn.execute("SELECT 1 FROM PRODUIT WHERE refprod = ?", (refprod,)).fetchone() is not None


def commande_existe(conn, numcde):
    return conn.execute("SELECT 1 FROM COMMANDE WHERE numcde = ?", (numcde,)).fetchone() is not None


def ligne_existe(conn, numcde, refprod):
    return conn.execute(
        "SELECT 1 FROM COMMANDER WHERE numcde = ? AND refprod = ?", (numcde, refprod)
    ).fetchone() is not None


def enregistrer_client(conn, code, nom, prenom, sexe, tel, ville):
    conn.execute("INSERT INTO CLIENT VALUES (?,?,?,?,?,?)",
                 (code, nom, prenom, sexe, tel, ville))
    conn.commit()


def enregistrer_commande(conn, numcde, codcli, codedeleg, datecde=None):
    if datecde is None:
        datecde = date.today().isoformat()
    conn.execute("INSERT INTO COMMANDE VALUES (?,?,?,?)",
                 (numcde, datecde, codcli, codedeleg))
    conn.commit()


def ajouter_produit_commande(conn, numcde, refprod, quantite):
    conn.execute("INSERT INTO COMMANDER VALUES (?,?,?)",
                 (numcde, refprod, quantite))
    conn.commit()


def consulter_commande(conn, numcde):
    return conn.execute("SELECT * FROM COMMANDE WHERE numcde = ?", (numcde,)).fetchone()


def commandes_du_client(conn, codcli):
    return conn.execute(
        "SELECT * FROM COMMANDE WHERE codcli = ? ORDER BY datecde", (codcli,)
    ).fetchall()


def modifier_quantite(conn, numcde, refprod, nouvelle_quantite):
    conn.execute(
        "UPDATE COMMANDER SET quantite = ? WHERE numcde = ? AND refprod = ?",
        (nouvelle_quantite, numcde, refprod))
    conn.commit()


def supprimer_ligne(conn, numcde, refprod):
    conn.execute(
        "DELETE FROM COMMANDER WHERE numcde = ? AND refprod = ?", (numcde, refprod))
    conn.commit()


def calculer_montant(conn, numcde):
    row = conn.execute("""
        SELECT SUM(p.prixunit * c.quantite) AS total
        FROM COMMANDER c JOIN PRODUIT p ON p.refprod = c.refprod
        WHERE c.numcde = ?
    """, (numcde,)).fetchone()
    return row["total"] if row["total"] is not None else 0


def lignes_commande(conn, numcde):
    return conn.execute("""
        SELECT p.refprod, p.libprod, p.prixunit, c.quantite,
               (p.prixunit * c.quantite) AS sous_total
        FROM COMMANDER c JOIN PRODUIT p ON p.refprod = c.refprod
        WHERE c.numcde = ?
    """, (numcde,)).fetchall()


def afficher_commandes_client(conn, codcli):
    resultat = []
    for cde in commandes_du_client(conn, codcli):
        montant = calculer_montant(conn, cde["numcde"])
        resultat.append((cde["numcde"], cde["datecde"], montant))
    return resultat


def menu():
    conn = connecter("commandes.db")
    creer_tables(conn)

    conn.execute("INSERT OR IGNORE INTO DELEGUE VALUES (?,?,?,?,?)",
                 ("D001", "GBAGUIDI", "Marc", "97000000", 150000))
    conn.execute("INSERT OR IGNORE INTO PRODUIT VALUES (?,?,?)",
                 ("P001", "Clavier", 8000))
    conn.execute("INSERT OR IGNORE INTO PRODUIT VALUES (?,?,?)",
                 ("P002", "Souris", 3500))
    conn.commit()

    while True:
        print("\n--- GESTION DES COMMANDES ---")
        print("1. Enregistrer un client")
        print("2. Enregistrer une commande")
        print("3. Ajouter un produit a une commande")
        print("4. Consulter une commande")
        print("5. Rechercher les commandes d'un client")
        print("6. Modifier une quantite commandee")
        print("7. Supprimer une ligne de commande")
        print("8. Calculer le montant d'une commande")
        print("9. Afficher toutes les commandes d'un client")
        print("0. Quitter")
        choix = input("Choix : ").strip()

        if choix == "1":
            code = saisir_code("Code client", FORMAT_CODCLI, "C001")
            if client_existe(conn, code):
                print("  -> Ce code client existe deja.")
                continue
            nom = saisir_texte_non_vide("Nom")
            prenom = saisir_texte_non_vide("Prenom")
            sexe = saisir_sexe()
            tel = saisir_telephone()
            ville = saisir_texte_non_vide("Ville")
            enregistrer_client(conn, code, nom, prenom, sexe, tel, ville)
            print("Client enregistre avec succes.")

        elif choix == "2":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            if commande_existe(conn, numcde):
                print("  -> Ce numero de commande existe deja.")
                continue
            codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
            if not client_existe(conn, codcli):
                print("  -> Ce client n'existe pas.")
                continue
            codedeleg = saisir_code("Code delegue", FORMAT_CODEDELEG, "D001")
            if not delegue_existe(conn, codedeleg):
                print("  -> Ce delegue n'existe pas.")
                continue
            enregistrer_commande(conn, numcde, codcli, codedeleg)
            print("Commande enregistree avec succes.")

        elif choix == "3":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            if not commande_existe(conn, numcde):
                print("  -> Cette commande n'existe pas.")
                continue
            refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
            if not produit_existe(conn, refprod):
                print("  -> Ce produit n'existe pas.")
                continue
            quantite = saisir_entier_positif("Quantite")
            ajouter_produit_commande(conn, numcde, refprod, quantite)
            print("Produit ajoute a la commande.")

        elif choix == "4":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            cde = consulter_commande(conn, numcde)
            if cde:
                print(dict(cde))
                for ligne in lignes_commande(conn, numcde):
                    print("   ", dict(ligne))
                print("   Montant total :", calculer_montant(conn, numcde))
            else:
                print("Commande introuvable.")

        elif choix == "5":
            codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
            commandes = commandes_du_client(conn, codcli)
            if not commandes:
                print("Aucune commande trouvee pour ce client.")
            for cde in commandes:
                print(dict(cde))

        elif choix == "6":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
            if not ligne_existe(conn, numcde, refprod):
                print("  -> Cette ligne de commande n'existe pas.")
                continue
            quantite = saisir_entier_positif("Nouvelle quantite")
            modifier_quantite(conn, numcde, refprod, quantite)
            print("Quantite modifiee avec succes.")

        elif choix == "7":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            refprod = saisir_code("Reference produit", FORMAT_REFPROD, "P001")
            if not ligne_existe(conn, numcde, refprod):
                print("  -> Cette ligne de commande n'existe pas.")
                continue
            reponse = input("Confirmer la suppression ? O/N : ").strip().upper()
            if reponse == "O":
                supprimer_ligne(conn, numcde, refprod)
                print("Ligne supprimee avec succes.")
            else:
                print("Suppression annulee.")

        elif choix == "8":
            numcde = saisir_code("Numero de commande", FORMAT_NUMCDE, "CDE001")
            if not commande_existe(conn, numcde):
                print("  -> Cette commande n'existe pas.")
                continue
            print("Montant total :", calculer_montant(conn, numcde), "francs")

        elif choix == "9":
            codcli = saisir_code("Code client", FORMAT_CODCLI, "C001")
            resultat = afficher_commandes_client(conn, codcli)
            if not resultat:
                print("Aucune commande trouvee pour ce client.")
            for numcde, datecde, montant in resultat:
                print(f"Commande {numcde} | {datecde} | Montant: {montant}")

        elif choix == "0":
            conn.close()
            print("Au revoir.")
            break

        else:
            print("Choix invalide.")


if __name__ == "__main__":
    menu()
