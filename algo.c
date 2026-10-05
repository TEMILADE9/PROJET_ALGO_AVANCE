#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sqlite3.h>

sqlite3 *connecter(const char *nomBase) {
    sqlite3 *db;
    if (sqlite3_open(nomBase, &db) != SQLITE_OK) {
        fprintf(stderr, "Erreur ouverture base : %s\n", sqlite3_errmsg(db));
        exit(1);
    }
    sqlite3_exec(db, "PRAGMA foreign_keys = ON;", NULL, NULL, NULL);
    return db;
}

void creerTables(sqlite3 *db) {
    const char *sql =
        "CREATE TABLE IF NOT EXISTS DELEGUE ("
        "  codedeleg TEXT PRIMARY KEY, nomdeleg TEXT NOT NULL,"
        "  prenomdeleg TEXT, telephone TEXT, salaire REAL);"
        "CREATE TABLE IF NOT EXISTS CLIENT ("
        "  codcli TEXT PRIMARY KEY, nomcli TEXT NOT NULL,"
        "  prenomcli TEXT, sexecli TEXT, telcli TEXT, villecli TEXT);"
        "CREATE TABLE IF NOT EXISTS PRODUIT ("
        "  refprod TEXT PRIMARY KEY, libprod TEXT NOT NULL, prixunit REAL NOT NULL);"
        "CREATE TABLE IF NOT EXISTS COMMANDE ("
        "  numcde TEXT PRIMARY KEY, datecde TEXT NOT NULL,"
        "  codcli TEXT NOT NULL, codedeleg TEXT NOT NULL,"
        "  FOREIGN KEY (codcli) REFERENCES CLIENT(codcli),"
        "  FOREIGN KEY (codedeleg) REFERENCES DELEGUE(codedeleg));"
        "CREATE TABLE IF NOT EXISTS COMMANDER ("
        "  numcde TEXT NOT NULL, refprod TEXT NOT NULL, quantite INTEGER NOT NULL,"
        "  PRIMARY KEY (numcde, refprod),"
        "  FOREIGN KEY (numcde) REFERENCES COMMANDE(numcde) ON DELETE CASCADE,"
        "  FOREIGN KEY (refprod) REFERENCES PRODUIT(refprod));";
    char *erreur = NULL;
    if (sqlite3_exec(db, sql, NULL, NULL, &erreur) != SQLITE_OK) {
        fprintf(stderr, "Erreur creation tables : %s\n", erreur);
        sqlite3_free(erreur);
    }
}

void lireLigne(char *buffer, int taille) {
    if (fgets(buffer, taille, stdin) != NULL) {
        size_t len = strlen(buffer);
        if (len > 0 && buffer[len - 1] == '\n')
            buffer[len - 1] = '\0';
    } else {
        buffer[0] = '\0';
    }
}

void versMajuscule(char *s) {
    for (int i = 0; s[i]; i++)
        s[i] = toupper((unsigned char)s[i]);
}

int formatValide(const char *valeur, const char *prefixe, int nbChiffres) {
    int lenPrefixe = strlen(prefixe);
    int lenValeur = strlen(valeur);
    if (lenValeur != lenPrefixe + nbChiffres)
        return 0;
    if (strncmp(valeur, prefixe, lenPrefixe) != 0)
        return 0;
    for (int i = lenPrefixe; i < lenValeur; i++) {
        if (!isdigit((unsigned char)valeur[i]))
            return 0;
    }
    return 1;
}

void saisirCode(char *resultat, int taille, const char *libelle,
                const char *prefixe, int nbChiffres, const char *exemple) {
    while (1) {
        printf("%s (format : %s) : ", libelle, exemple);
        lireLigne(resultat, taille);
        versMajuscule(resultat);
        if (formatValide(resultat, prefixe, nbChiffres))
            return;
        printf("  -> Format invalide. Exemple attendu : %s\n", exemple);
    }
}

void saisirTexteNonVide(char *resultat, int taille, const char *libelle) {
    while (1) {
        printf("%s : ", libelle);
        lireLigne(resultat, taille);
        if (strlen(resultat) > 0)
            return;
        printf("  -> Ce champ ne peut pas etre vide.\n");
    }
}

char saisirSexe(void) {
    char buffer[10];
    while (1) {
        printf("Sexe (M/F) : ");
        lireLigne(buffer, sizeof(buffer));
        versMajuscule(buffer);
        if (strcmp(buffer, "M") == 0 || strcmp(buffer, "F") == 0)
            return buffer[0];
        printf("  -> Valeur invalide. Le sexe doit etre M ou F uniquement.\n");
    }
}

void saisirTelephone(char *resultat, int taille) {
    while (1) {
        printf("Telephone (8 chiffres) : ");
        lireLigne(resultat, taille);
        int ok = (strlen(resultat) == 8);
        for (int i = 0; ok && resultat[i]; i++)
            if (!isdigit((unsigned char)resultat[i])) ok = 0;
        if (ok) return;
        printf("  -> Telephone invalide. Il doit contenir exactement 8 chiffres.\n");
    }
}

int saisirEntierPositif(const char *libelle) {
    char buffer[20];
    while (1) {
        printf("%s : ", libelle);
        lireLigne(buffer, sizeof(buffer));
        int ok = (strlen(buffer) > 0);
        for (int i = 0; ok && buffer[i]; i++)
            if (!isdigit((unsigned char)buffer[i])) ok = 0;
        if (ok) {
            int valeur = atoi(buffer);
            if (valeur > 0) return valeur;
        }
        printf("  -> %s invalide. Ce doit etre un entier strictement positif.\n", libelle);
    }
}

int existeDans(sqlite3 *db, const char *table, const char *colonne, const char *valeur) {
    char sql[150];
    snprintf(sql, sizeof(sql), "SELECT 1 FROM %s WHERE %s = ?", table, colonne);
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, valeur, -1, SQLITE_STATIC);
    int trouve = (sqlite3_step(stmt) == SQLITE_ROW);
    sqlite3_finalize(stmt);
    return trouve;
}

int ligneExiste(sqlite3 *db, const char *numcde, const char *refprod) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "SELECT 1 FROM COMMANDER WHERE numcde = ? AND refprod = ?", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, refprod, -1, SQLITE_STATIC);
    int trouve = (sqlite3_step(stmt) == SQLITE_ROW);
    sqlite3_finalize(stmt);
    return trouve;
}

void enregistrerClient(sqlite3 *db, const char *code, const char *nom,
                        const char *prenom, char sexe, const char *tel,
                        const char *ville) {
    sqlite3_stmt *stmt;
    char sexeStr[2] = {sexe, '\0'};
    sqlite3_prepare_v2(db, "INSERT INTO CLIENT VALUES (?,?,?,?,?,?)", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, code, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, nom, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, prenom, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, sexeStr, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 5, tel, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 6, ville, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void enregistrerCommande(sqlite3 *db, const char *numcde, const char *datecde,
                          const char *codcli, const char *codedeleg) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db, "INSERT INTO COMMANDE VALUES (?,?,?,?)", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, datecde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, codcli, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, codedeleg, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void ajouterProduitCommande(sqlite3 *db, const char *numcde, const char *refprod, int quantite) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db, "INSERT INTO COMMANDER VALUES (?,?,?)", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, refprod, -1, SQLITE_STATIC);
    sqlite3_bind_int(stmt, 3, quantite);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

int consulterCommande(sqlite3 *db, const char *numcde) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db, "SELECT * FROM COMMANDE WHERE numcde = ?", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    int trouve = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        trouve = 1;
        printf("Commande %s | Date: %s | Client: %s | Delegue: %s\n",
               sqlite3_column_text(stmt, 0), sqlite3_column_text(stmt, 1),
               sqlite3_column_text(stmt, 2), sqlite3_column_text(stmt, 3));
    }
    sqlite3_finalize(stmt);
    return trouve;
}

void afficherLignesCommande(sqlite3 *db, const char *numcde) {
    sqlite3_stmt *stmt;
    const char *sql =
        "SELECT p.refprod, p.libprod, p.prixunit, c.quantite, "
        "(p.prixunit * c.quantite) AS sous_total "
        "FROM COMMANDER c JOIN PRODUIT p ON p.refprod = c.refprod WHERE c.numcde = ?";
    sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        printf("    %s | %s | PU: %.2f | Qte: %d | Sous-total: %.2f\n",
               sqlite3_column_text(stmt, 0), sqlite3_column_text(stmt, 1),
               sqlite3_column_double(stmt, 2), sqlite3_column_int(stmt, 3),
               sqlite3_column_double(stmt, 4));
    }
    sqlite3_finalize(stmt);
}

int commandesDuClient(sqlite3 *db, const char *codcli) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "SELECT * FROM COMMANDE WHERE codcli = ? ORDER BY datecde", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, codcli, -1, SQLITE_STATIC);
    int compteur = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        printf("Commande %s | Date: %s | Delegue: %s\n",
               sqlite3_column_text(stmt, 0), sqlite3_column_text(stmt, 1),
               sqlite3_column_text(stmt, 3));
        compteur++;
    }
    sqlite3_finalize(stmt);
    return compteur;
}

void modifierQuantite(sqlite3 *db, const char *numcde, const char *refprod, int nouvelleQte) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "UPDATE COMMANDER SET quantite = ? WHERE numcde = ? AND refprod = ?",
        -1, &stmt, NULL);
    sqlite3_bind_int(stmt, 1, nouvelleQte);
    sqlite3_bind_text(stmt, 2, numcde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, refprod, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void supprimerLigne(sqlite3 *db, const char *numcde, const char *refprod) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "DELETE FROM COMMANDER WHERE numcde = ? AND refprod = ?", -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, refprod, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

double calculerMontant(sqlite3 *db, const char *numcde) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "SELECT SUM(p.prixunit * c.quantite) FROM COMMANDER c "
        "JOIN PRODUIT p ON p.refprod = c.refprod WHERE c.numcde = ?",
        -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, numcde, -1, SQLITE_STATIC);
    double total = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW)
        total = sqlite3_column_double(stmt, 0);
    sqlite3_finalize(stmt);
    return total;
}

int afficherCommandesClientAvecMontant(sqlite3 *db, const char *codcli) {
    sqlite3_stmt *stmt;
    sqlite3_prepare_v2(db,
        "SELECT numcde, datecde FROM COMMANDE WHERE codcli = ? ORDER BY datecde",
        -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, codcli, -1, SQLITE_STATIC);
    int compteur = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        const unsigned char *numcde = sqlite3_column_text(stmt, 0);
        const unsigned char *datecde = sqlite3_column_text(stmt, 1);
        double montant = calculerMontant(db, (const char *)numcde);
        printf("Commande %s | %s | Montant: %.2f\n", numcde, datecde, montant);
        compteur++;
    }
    sqlite3_finalize(stmt);
    return compteur;
}

int main(void) {
    sqlite3 *db = connecter("commandes.db");
    creerTables(db);

    sqlite3_exec(db,
        "INSERT OR IGNORE INTO DELEGUE VALUES ('D001','GBAGUIDI','Marc','97000000',150000);",
        NULL, NULL, NULL);
    sqlite3_exec(db,
        "INSERT OR IGNORE INTO PRODUIT VALUES ('P001','Clavier',8000);",
        NULL, NULL, NULL);
    sqlite3_exec(db,
        "INSERT OR IGNORE INTO PRODUIT VALUES ('P002','Souris',3500);",
        NULL, NULL, NULL);

    char choix[10];
    char code[20], numcde[20], refprod[20], codedeleg[20];
    char nom[50], prenom[50], tel[20], ville[50];

    while (1) {
        printf("\n--- GESTION DES COMMANDES ---\n");
        printf("1. Enregistrer un client\n");
        printf("2. Enregistrer une commande\n");
        printf("3. Ajouter un produit a une commande\n");
        printf("4. Consulter une commande\n");
        printf("5. Rechercher les commandes d'un client\n");
        printf("6. Modifier une quantite commandee\n");
        printf("7. Supprimer une ligne de commande\n");
        printf("8. Calculer le montant d'une commande\n");
        printf("9. Afficher toutes les commandes d'un client\n");
        printf("0. Quitter\n");
        printf("Choix : ");
        lireLigne(choix, sizeof(choix));

        if (strcmp(choix, "1") == 0) {
            saisirCode(code, sizeof(code), "Code client", "C", 3, "C001");
            if (existeDans(db, "CLIENT", "codcli", code)) {
                printf("  -> Ce code client existe deja.\n");
                continue;
            }
            saisirTexteNonVide(nom, sizeof(nom), "Nom");
            saisirTexteNonVide(prenom, sizeof(prenom), "Prenom");
            char sexe = saisirSexe();
            saisirTelephone(tel, sizeof(tel));
            saisirTexteNonVide(ville, sizeof(ville), "Ville");
            enregistrerClient(db, code, nom, prenom, sexe, tel, ville);
            printf("Client enregistre avec succes.\n");

        } else if (strcmp(choix, "2") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            if (existeDans(db, "COMMANDE", "numcde", numcde)) {
                printf("  -> Ce numero de commande existe deja.\n");
                continue;
            }
            saisirCode(code, sizeof(code), "Code client", "C", 3, "C001");
            if (!existeDans(db, "CLIENT", "codcli", code)) {
                printf("  -> Ce client n'existe pas.\n");
                continue;
            }
            saisirCode(codedeleg, sizeof(codedeleg), "Code delegue", "D", 3, "D001");
            if (!existeDans(db, "DELEGUE", "codedeleg", codedeleg)) {
                printf("  -> Ce delegue n'existe pas.\n");
                continue;
            }
            enregistrerCommande(db, numcde, "2026-10-04", code, codedeleg);
            printf("Commande enregistree avec succes.\n");

        } else if (strcmp(choix, "3") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            if (!existeDans(db, "COMMANDE", "numcde", numcde)) {
                printf("  -> Cette commande n'existe pas.\n");
                continue;
            }
            saisirCode(refprod, sizeof(refprod), "Reference produit", "P", 3, "P001");
            if (!existeDans(db, "PRODUIT", "refprod", refprod)) {
                printf("  -> Ce produit n'existe pas.\n");
                continue;
            }
            int quantite = saisirEntierPositif("Quantite");
            ajouterProduitCommande(db, numcde, refprod, quantite);
            printf("Produit ajoute a la commande.\n");

        } else if (strcmp(choix, "4") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            if (consulterCommande(db, numcde)) {
                afficherLignesCommande(db, numcde);
                printf("    Montant total : %.2f\n", calculerMontant(db, numcde));
            } else {
                printf("Commande introuvable.\n");
            }

        } else if (strcmp(choix, "5") == 0) {
            saisirCode(code, sizeof(code), "Code client", "C", 3, "C001");
            if (commandesDuClient(db, code) == 0)
                printf("Aucune commande trouvee pour ce client.\n");

        } else if (strcmp(choix, "6") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            saisirCode(refprod, sizeof(refprod), "Reference produit", "P", 3, "P001");
            if (!ligneExiste(db, numcde, refprod)) {
                printf("  -> Cette ligne de commande n'existe pas.\n");
                continue;
            }
            int quantite = saisirEntierPositif("Nouvelle quantite");
            modifierQuantite(db, numcde, refprod, quantite);
            printf("Quantite modifiee avec succes.\n");

        } else if (strcmp(choix, "7") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            saisirCode(refprod, sizeof(refprod), "Reference produit", "P", 3, "P001");
            if (!ligneExiste(db, numcde, refprod)) {
                printf("  -> Cette ligne de commande n'existe pas.\n");
                continue;
            }
            char reponse[10];
            printf("Confirmer la suppression ? O/N : ");
            lireLigne(reponse, sizeof(reponse));
            versMajuscule(reponse);
            if (strcmp(reponse, "O") == 0) {
                supprimerLigne(db, numcde, refprod);
                printf("Ligne supprimee avec succes.\n");
            } else {
                printf("Suppression annulee.\n");
            }

        } else if (strcmp(choix, "8") == 0) {
            saisirCode(numcde, sizeof(numcde), "Numero de commande", "CDE", 3, "CDE001");
            if (!existeDans(db, "COMMANDE", "numcde", numcde)) {
                printf("  -> Cette commande n'existe pas.\n");
                continue;
            }
            printf("Montant total : %.2f francs\n", calculerMontant(db, numcde));

        } else if (strcmp(choix, "9") == 0) {
            saisirCode(code, sizeof(code), "Code client", "C", 3, "C001");
            if (afficherCommandesClientAvecMontant(db, code) == 0)
                printf("Aucune commande trouvee pour ce client.\n");

        } else if (strcmp(choix, "0") == 0) {
            sqlite3_close(db);
            printf("Au revoir.\n");
            break;

        } else {
            printf("Choix invalide.\n");
        }
    }

    return 0;
}
