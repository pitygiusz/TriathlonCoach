import streamlit as st
from datetime import datetime
import pandas as pd

from database import init_db, add_workout, get_workouts, delete_workout, get_coach_logs, save_coach_log, update_workout
from coach import ask_coach, summary_all, kitchen_help, gym_plan



# --- INTERFEJS STREAMLIT ---
st.set_page_config(page_title="Triathlon Coach", layout="centered")

st.title("Triathlon Coach")

goals = {
    "SuperSprint Grudziądz": datetime(2026, 6, 14),
    "1/2 IM Malbork": datetime(2026, 9, 6)
}

cols = st.columns(len(goals))
for i, (goal, date) in enumerate(goals.items()):
    delta = date- datetime.now()
    if delta.days >= 0:
        cols[i].metric(goal, f"{delta.days} dni", delta=None)
    else:
        cols[i].metric(goal, "Zawody już się odbyły!", delta=None)

# Inicjalizacja bazy przy starcie
init_db()

tab1, tab2, tab3 = st.tabs(["Treningi", "Statystyki", "Trener"])

with tab1:
    st.header("Moje treningi")
    st.subheader("Dodaj nowy trening")
    with st.form("workout_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Data", datetime.now())
            
        with col2:
            discipline = st.selectbox("Dyscyplina", ["Pływanie", "Rower", "Bieg", "Siłownia", "Inne"])
            
            
        col1, col2, col3 = st.columns(3)
        with col1:
            distance = st.number_input("Dystans (km)", min_value=0.0, step=1.0)
        with col2:
            duration = st.number_input("Czas (min)", min_value=0, step=10)
        with col3:
            avg_heart_rate = st.number_input("Średnie tętno (bpm)", min_value=0, step=1)
            
        rpe = st.slider("RPE (Odczucie zmęczenia 1-10)", 1, 10, 5)
        notes = st.text_area("Notatki")
        
        submitted = st.form_submit_button("Zapisz trening")
        if submitted:
            add_workout(date, discipline, duration, distance, rpe, avg_heart_rate, notes)
            st.success("Trening zapisany! Dobra robota.")

    st.subheader("Edytuj ostatnie treningi")
    df = get_workouts(5) 
    if not df.empty:
        df.insert(0, "delete", False)

        edited_df = st.data_editor(
            df,
            key="data_editor_tab1",
            hide_index=True,  
            column_config={
                "delete": st.column_config.CheckboxColumn(
                    "Usuń",
                    default=False,
                ),
                "id": None,
            },
        )

        col1, col2 = st.columns(2)
        
        # PRZYCISK 1: Zapisywanie edycji
        with col1:
            if st.button("Zapisz zmiany w tabeli", type="primary", use_container_width=True):
                # Zabezpieczenie: Zamieniamy puste komórki na odpowiednie formaty, żeby baza nie dostała błędu NaN
                edited_df.fillna({"notes": "", "avg_heart_rate": 0, "distance_km": 0.0}, inplace=True)
                
                # Przechodzimy przez każdy wiersz w tabeli na ekranie
                for index, row in edited_df.iterrows():
                    if not row["delete"]: # Ignorujemy te, które są zaznaczone do usunięcia
                        update_workout(
                            workout_id=row['id'],
                            date=row['date'],
                            discipline=row['discipline'],
                            duration=row['duration_minutes'],
                            distance=row['distance_km'],
                            rpe=row['rpe'],
                            avg_heart_rate=row['avg_heart_rate'],
                            notes=row['notes']
                        )
                st.success("Zapisano zmiany!")
                st.rerun() # Odświeża aplikację

        # PRZYCISK 2: Usuwanie 
        with col2:
            if st.button("Usuń zaznaczone", use_container_width=True):
                to_delete = edited_df[edited_df["delete"] == True]

                if not to_delete.empty:
                    for index, row in to_delete.iterrows():
                        delete_workout(row["id"])

                    st.success(f"Usunięto {len(to_delete)} trening(ów).")
                    st.rerun() 
                else:
                    st.warning("Nie zaznaczono żadnego treningu do usunięcia.")
    else:
        st.info("Brak zapisanych treningów.")

    st.markdown("")
    with st.expander("Pokaż wszystkie treningi"):
        df = get_workouts() 
        if not df.empty:
            st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            st.info("Brak zapisanych treningów.")

with tab2:
    st.header("Statystyki treningowe")
    df = get_workouts()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

        total_time = df['duration_minutes'].sum()
        total_distance = df['distance_km'].sum()

        st.subheader("Podsumowanie")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Łączny czas treningów (min)", total_time)
        with col2:
            st.metric("Łączny dystans (km)", round(total_distance,2))

        sport1, sport2, sport3 = st.columns(3)
        with sport1:
            swim_df = df[df['discipline'] == 'Pływanie']
            st.metric("Liczba treningów pływackich", len(swim_df), )
        with sport2:
            bike_df = df[df['discipline'] == 'Rower']
            st.metric("Liczba treningów rowerowych", len(bike_df))
        with sport3:
            run_df = df[df['discipline'] == 'Bieg']
            st.metric("Liczba treningów biegowych", len(run_df))
        


        st.subheader("Treningi w czasie")
        st.bar_chart(df, x='date', y='duration_minutes', color = 'discipline', use_container_width=True)

        st.subheader("Wnioski")

        if st.button("Generuj wnioski", key="analyze_button"):
            with st.spinner("Generowanie..."):
                history = get_workouts(100) 
                if not history.empty:
                    summary, cost = summary_all(history)
                    st.markdown(summary)
                    st.caption(f"Szacunkowy koszt analizy: ${cost:.6f}")
                else:
                    st.warning("Brak danych w historii.")

with tab3:
    st.header("Konsultacja z trenerem")
    st.write("Wybierz, co chesz uwzględnić w analizie trenera:")
    col1, col2 = st.columns(2)
    with col1:
        include_competition = st.toggle("Terminy zawodów", value=True)
    #competition = st.selectbox("Wybierz zawody", ['SuperSprint Grudziądz 14.06', '1/2 IM Malbork 06.09'])
        include_weather = st.toggle("Prognoza pogody", value=True)
    with col2:
        include_long_term = st.toggle("Długoterminowa baza", value=True)

        easier_week = st.toggle("Łatwiejszy tydzień", value=False)

    #st.write("Kliknij poniżej, aby wysłać swoje logi z ostatnich 7 dni do analizy.")
    latest_advice, advice_date = get_coach_logs()

    if st.button("Wyślij do trenera", key="coach_button"):
            with st.spinner("Generowanie..."):
                history = get_workouts(14) 
                if not history.empty:
                    advice, cost, prompt = ask_coach(history, include_competition, include_weather, easier_week, include_long_term)
                    st.session_state['last_gen_cost'] = cost
                    st.session_state['last_gen_prompt'] = prompt

                    st.markdown("### Raport Trenera:")
                    st.markdown(advice)
                    save_coach_log(advice)
                
                    st.rerun()  # Odśwież stronę, aby zobaczyć nową analizę
                else:
                    st.warning("Brak danych z ostatnich 7 dni.")

    if latest_advice:
        st.success(f"Ostatnia analiza trenera z dnia {advice_date}:")
        st.markdown(latest_advice)
        

    else:
        st.info("Brak wcześniejszych analiz trenera. Wyślij swoje logi, aby otrzymać pierwszą analizę.")
    
    st.markdown("---")
    if 'last_gen_cost' in st.session_state and 'last_gen_prompt' in st.session_state:
            st.caption(f"Szacunkowy koszt analizy: ${st.session_state['last_gen_cost']:.6f}")
            with st.expander("Podgląd prompta trenera"):
                st.code(st.session_state['last_gen_prompt'])
    with st.expander("Pokaż archiwum analiz trenera"):
        coach_history = get_coach_logs(10)

        if not coach_history.empty:
            for index, row in coach_history.iterrows():
                with st.expander(f"Analiza z {row['date']}"):
                    st.markdown(row['advice'])
        else:
            st.info("Brak zapisanych analiz trenera.")







    


