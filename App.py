from math import prod
import streamlit as st
import pandas as pd
import numpy as np
import re
import random
import plotly.express as px


st.set_page_config(page_title="Machine Steel")


def loadData(dir=r"https://res.cloudinary.com/camilo203/raw/upload/v1632715854/Archivo_Tablas_Entrega_Intermedia_ezqmpk.xlsx"):
    data = pd.read_excel(
        dir,engine="openpyxl"
    )
    Productos = data.iloc[0:17, 0:4].copy()
    Productos.columns = Productos.iloc[0]
    Productos = Productos.drop(0, axis=0)
    Productos = Productos.set_index("Número de producto")
    Productos.Secuencia = Productos.Secuencia.apply(
        lambda x: list(map(int, x.split("-")))
    )
    Estaciones = data.iloc[19:33].copy()
    Estaciones.columns = Estaciones.iloc[0]
    Estaciones = Estaciones.drop(19)
    Estaciones = Estaciones.set_index("Estación")
    Estaciones.columns.name = ""
    Estaciones = Estaciones.replace(np.nan, 0.0)
    Recursos = data.iloc[35:47, 0:2].copy()
    Recursos.columns = Recursos.iloc[0]
    Recursos.columns.name = ""
    Recursos = Recursos.set_index("Recurso")
    Recursos = Recursos.drop("Recurso")
    indexes = []
    for index in Recursos.index:
        val = re.search("(?<=\[).+(?=\])", index)[0]
        divisor = re.search("\d+(?= |\w)", val)
        if divisor:
            div = float(divisor[0])
            a = val[: re.search("\d+(?= |\w)", val).span()[1]]
            a = index.replace(a, "")
            indexes.append(a)
        else:
            indexes.append(index)
            div = 1

        Recursos.loc[index][0] /= div
    Recursos.index = indexes
    ManoDeObra = data.iloc[48:50, 0:2].copy()
    ManoDeObra.columns = ManoDeObra.iloc[0]
    ManoDeObra = ManoDeObra.drop(48)
    ManoDeObra = ManoDeObra.set_index("Mano de obra mensual")
    ManoDeObra.columns.name = ""
    MO = ManoDeObra
    ManoDeObraMes = ManoDeObra.iloc[0][0]
    Gastos = data.iloc[51:54, 0:2].copy()
    Gastos.columns = Gastos.iloc[0]
    Gastos.columns.name = ""
    Gastos = Gastos.drop(51)
    CostoMovimiento = data.iloc[55:57, 0:2]
    CostoMovimiento.columns = CostoMovimiento.iloc[0]
    CostoMovimiento.drop(55, inplace=True)
    CostoMovimiento.columns.name = ""
    CostoMovimiento = CostoMovimiento.set_index("Movimiento de unidad de producto")
    CM = CostoMovimiento
    CostoMovimiento = CostoMovimiento.iloc[0][0]
    Precios = data.iloc[60:, 0:2]
    Precios.columns = Precios.iloc[0]
    Precios.drop(60, inplace=True)
    Precios.set_index("Producto", inplace=True)
    Precios.columns.name = ""

    return (
        Productos,
        Estaciones,
        Recursos,
        MO,
        ManoDeObraMes,
        Gastos,
        CM,
        CostoMovimiento,
        Precios,
    )





def procesarDatos(
    Productos, Estaciones, Recursos, ManoDeObraMes, Gastos, CostoMovimiento, Precios, MDist=r"https://res.cloudinary.com/camilo203/raw/upload/v1633291086/MatrizD_m5kex6.xlsx"
):
    MatrizDistancia = pd.read_excel(MDist,engine="openpyxl")
    MatrizDistancia = MatrizDistancia.set_index("Estación")
    MatrizDistancia.columns.name = "Estación"
    MatrizDistancia.index.name = ""
    MatrizFlujos = MatrizDistancia.copy()
    MatrizFlujos[:] = np.zeros((13, 13))
    CostosEstaciones = pd.DataFrame()
    CostosEstaciones[[x for x in range(1, 14)]] = np.zeros(13)
    CostosEstaciones.loc["$MO"] = np.zeros(13)
    CostosEstaciones.loc["$MP"] = np.zeros(13)
    CostosEstaciones.loc["Tiempo"] = np.zeros(13)
    CostosProds = {}
    for producto in Productos.index:
        ruta = Productos.loc[producto]["Secuencia"]
        costoTotal = 0
        costoMP = 0
        costoMO = 0
        costoTrans = 0
        tiempoTotal = 0
        demanda = Productos.loc[producto]["Demanda mensual"]
        necesarios = demanda
        for i in range(len(ruta) - 1, -1, -1):
            estas = ruta[i]
            cMOEs = 0
            cMPEs = 0
            tEs = 0
            if i != 0:
                estacion = Estaciones.loc[ruta[i]]
                costoTransporte = (
                    CostoMovimiento * MatrizDistancia.loc[ruta[i - 1], ruta[i]]
                )
                necesarios *= 1 + estacion["Defectos no reparables por estación"]
                necesarios = np.ceil(necesarios)
                tNecesMin = estacion["Tiempo de producción min"]
                defectos = necesarios * estacion["Defecto reparables por estación"]
                defectos = np.ceil(defectos)
                bien = necesarios - defectos
                recursos = estacion[3:].values / 480
                costosBien = bien * np.dot(Recursos["Costos"].values, recursos)
                costosDefect = defectos * np.dot(
                    Recursos["Costos"].values, recursos * 1.18
                )
                costoMP += costosBien + costosDefect
                cMPEs += costosBien + costosDefect
                costTBien = bien * tNecesMin * (ManoDeObraMes / 27 / 8 / 60)
                costTDefect = (
                    defectos * (tNecesMin * 1.45) * (ManoDeObraMes / 27 / 8 / 60)
                )
                costoMO += costTBien + costTDefect
                cMOEs += costTBien + costTDefect
                CostoTotalSinDefect = (
                    costosBien
                    + costosDefect
                    + costTBien
                    + costTDefect
                    + costoTransporte
                ) / demanda
                tiempoTotal += (tNecesMin * bien) + (tNecesMin * 1.45 * defectos)
                costoTrans += costoTransporte
                tEs += (tNecesMin * bien) + (tNecesMin * 1.45 * defectos)
                costoTotal += CostoTotalSinDefect
                MatrizFlujos.loc[ruta[i - 1], ruta[i]] += necesarios
            else:
                estacion = Estaciones.loc[ruta[i]]
                necesarios *= 1 + estacion["Defectos no reparables por estación"]
                necesarios = np.ceil(necesarios)
                tNecesMin = estacion["Tiempo de producción min"]
                defectos = necesarios * estacion["Defecto reparables por estación"]
                defectos = np.ceil(defectos)
                bien = necesarios - defectos
                recursos = estacion[3:].values / 480
                costosBien = bien * np.dot(Recursos["Costos"].values, recursos)
                costosDefect = defectos * np.dot(
                    Recursos["Costos"].values, recursos * 1.18
                )
                costoMP += costosBien + costosDefect
                costTBien = bien * tNecesMin * (ManoDeObraMes / 27 / 8 / 60)
                costTDefect = (
                    defectos * (tNecesMin * 1.45) * (ManoDeObraMes / 27 / 8 / 60)
                )
                costoMO += costTBien + costTDefect
                cMPEs += costosBien + costosDefect
                cMOEs += costTBien + costTDefect
                CostoTotalSinDefect = (
                    costosBien + costosDefect + costTBien + costTDefect
                ) / demanda
                tiempoTotal += (tNecesMin * bien) + (tNecesMin * 1.45 * defectos)
                costoTotal += CostoTotalSinDefect
            CostosEstaciones.loc["Tiempo", estas] += tEs
            CostosEstaciones.loc["$MO", estas] += cMOEs
            CostosEstaciones.loc["$MP", estas] += cMPEs

        CostosProds[Productos.loc[producto]["Producto"]] = {
            "CostoVariable": costoTotal,
            "TiempoNecesario": tiempoTotal,
            "ProductividadMO (und/min)": demanda / tiempoTotal,
            "ProductividadMP (und/$)": demanda / costoMP,
            "ProductividadMO (und/$)": demanda / costoMO,
            "ProductividadMO+MP (und/$)": demanda / (costoMO + costoMP),
            "ProdTxRef (\$/\$)": Precios.loc[producto][0]
            * demanda
            / (costoMO + costoMP + costoTrans),
        }
    CostosEstaciones.loc["Unidades"] = MatrizFlujos.apply(np.sum)
    CostosEstaciones.loc["ProdMO (und/min)"] = (
        CostosEstaciones.loc["Unidades"] / CostosEstaciones.loc["Tiempo"]
    )
    CostosEstaciones.loc["ProdMO (und/$)"] = (
        CostosEstaciones.loc["Unidades"] / CostosEstaciones.loc["$MO"]
    )
    CostosEstaciones.loc["ProdMP (und/$)"] = (
        CostosEstaciones.loc["Unidades"] / CostosEstaciones.loc["$MP"]
    )
    CostosEstaciones.loc["ProdMP+MO (und/$)"] = CostosEstaciones.loc["Unidades"] / (
        CostosEstaciones.loc["$MP"] + CostosEstaciones.loc["$MO"]
    )
    ProductProductos = pd.DataFrame(CostosProds)
    ProdTotal = ProductProductos.loc["ProdTxRef (\$/\$)"].mean()
    tiempoProd = list(map(lambda x: CostosProds[x]["TiempoNecesario"], CostosProds))
    CosteoABC = pd.DataFrame()
    arr = np.ndarray((2, 16))
    CosteoABC["Costo Indirecto"] = ["Arriendo", "GastosAdministrativos"]
    CosteoABC.index = ["Arriendo", "Gastos Administrativos"]
    CosteoABC.index.name = "Actividad"
    CosteoABC["Costo Indirecto"] = [Gastos.iloc[0, 1], Gastos.iloc[1, 1]]
    CosteoABC["Inductor"] = ["Tiempo total de producción", "Tiempo total de producción"]
    arr[0] = tiempoProd
    arr[1] = tiempoProd
    CosteoABC[list(map(lambda x: f"Tiempo x {x}", Productos.Producto.to_list()))] = arr
    CosteoABC[list(map(lambda x: f"% x {x}", Productos.Producto.to_list()))] = np.zeros(
        (2, 16)
    )
    for i in CosteoABC.iloc[:, 18:]:
        x = f"Tiempo x {i.split(' x ')[1]}"
        CosteoABC.loc["Arriendo", i] = CosteoABC.loc["Arriendo", x] / sum(tiempoProd)
        CosteoABC.loc["Gastos Administrativos", i] = CosteoABC.loc[
            "Gastos Administrativos", x
        ] / sum(tiempoProd)

    CosteoABC[list(map(lambda x: f"{x}", Productos.Producto.to_list()))] = np.zeros(
        (2, 16)
    )
    for i in CosteoABC.iloc[:, 34:]:
        x = f"% x {i}"
        CosteoABC.loc["Arriendo", i] = (
            CosteoABC.loc["Arriendo", "Costo Indirecto"] * CosteoABC.loc["Arriendo", x]
        )
        CosteoABC.loc["Gastos Administrativos", i] = (
            CosteoABC.loc["Gastos Administrativos", "Costo Indirecto"]
            * CosteoABC.loc["Gastos Administrativos", x]
        )

    a = CosteoABC.iloc[:, 34:].copy()
    a.loc["TotalFijo"] = np.zeros(16)
    a.loc["TotalFijo"] = a.apply(lambda x: x[0] + x[1])
    for i, j in enumerate(a, 1):
        a.loc["CostoUnitarioFijo", j] = (
            a.loc["TotalFijo", j] / Productos.loc[f"Prod{i}", "Demanda mensual"]
        )
    costoVar = list(map(lambda x: CostosProds[x]["CostoVariable"], CostosProds))
    a.loc["CostoVariableUnitario"] = costoVar
    a.loc["CostoTotalUnitario"] = a.apply(lambda x: x[3] + x[4])
    a.loc["PrecioDeVenta"] = Precios["Precio de venta unitario "].values
    a.loc["UtilidadUnitaria"] = (
        Precios["Precio de venta unitario "].values - a.loc["CostoTotalUnitario"].values
    )

    a.loc["UtilidadMensual"] = (
        Productos["Demanda mensual"].values * a.loc["UtilidadUnitaria"].values
    )
    UtilidadTotal = a.loc["UtilidadMensual"].sum()
    return ProductProductos, CostosEstaciones, a, ProdTotal, UtilidadTotal, MatrizDistancia

st.title("DashBoard Machine Steel")
st.markdown("[Descargue el archivo aqui](https://res.cloudinary.com/camilo203/raw/upload/v1632715854/Archivo_Tablas_Entrega_Intermedia_ezqmpk.xlsx)")
st.text_area("","Sí desea cambiar valor de algun dato descargue el archivo de link de arriba, modifique y agregue  aqui:")
fileN =  st.file_uploader("Ingrese el archivo aqui si modifico los datos:",".xlsx")

try:
    (
        Productos,
        Estaciones,
        Recursos,
        MO,
        ManoDeObraMes,
        Gastos,
        CM,
        CostoMovimiento,
        Precios,
    ) = loadData(fileN) if fileN else loadData() 
    (
        productividadProds,
        productividaEstaciones,
        costosTotales,
        prodTotal,
        utilidadTotal,
        MatrizDistancia
    ) = procesarDatos(
        Productos, Estaciones, Recursos, ManoDeObraMes, Gastos, CostoMovimiento, Precios
    )
    st.text("Tabla con la información de los productos de la empresa")
    Productos.Secuencia = Productos.Secuencia.apply(str)
    st.dataframe(Productos)
    st.text("Tabla con la información de las estaciones de la empresa")
    st.dataframe(Estaciones)
    st.text("Tabla con la información de los costos de los recursos")
    st.dataframe(Recursos)
    st.text("Tabla con la información de los costos de la mano de obra")
    st.dataframe(MO)
    st.text("Tabla con la información de los costos fijos")
    st.dataframe(Gastos)
    st.text("Tabla con la información del costo de transporte")
    st.dataframe(CM)
    st.text("Tabla con la información de los precios de los productos")
    st.dataframe(Precios)
    st.text("")
    st.text("La configuración actual de la empresa es la siguiente:")
    st.image(r"https://res.cloudinary.com/camilo203/image/upload/v1633291537/Configuraci%C3%B3nActualPlanta_zpa92t.png")
    st.text("Matriz de distancia entre estaciones:")
    st.dataframe(MatrizDistancia)


    st.subheader("Los indicadores de productividad y costos son los siguientes: ")
    productos = Productos.Producto.to_list()
    departamento_selec = st.multiselect("Escoga de que productos desea ver los costos totales:", productos, default=productos)

    st.text("Costos totales unitarios por producto")
    filtradosProds = costosTotales.loc["CostoTotalUnitario",departamento_selec] 
    filtradosProds.index.name = "Producto"
    bar_chart_costoProds = px.bar(filtradosProds,x=filtradosProds.index,y="CostoTotalUnitario", template="plotly_white")
    st.plotly_chart(bar_chart_costoProds)
    st.dataframe(filtradosProds)

    st.text("Rentabilidad Mensual de los productos")
    filtradosRentProds = costosTotales.loc["UtilidadMensual",departamento_selec] 
    filtradosRentProds.index.name = "Producto"
    bar_chart_rentProds = px.bar(filtradosRentProds,x=filtradosRentProds.index,y="UtilidadMensual", template="plotly_white")
    st.plotly_chart(bar_chart_rentProds)
    st.dataframe(filtradosRentProds)

    st.text("Indicadores de producitividad parciales y totales de mano de obra y materia prima por producto")
    filtradosProductProds = productividadProds.loc["ProductividadMP (und/$)":"ProductividadMO+MP (und/$)", departamento_selec].copy()
    filtradosProductProds = filtradosProductProds.T
    filtradosProductProds.index.name = "Productos"
    bar_chart_prodProds = px.bar(filtradosProductProds, x=filtradosProductProds.index, y =filtradosProductProds.columns ,barmode="group", template="plotly_white", title="Productividad (und/$) parciales y totales")
    bar_chart_prodProds.update_layout(yaxis_tickformat=".2e")
    st.plotly_chart(bar_chart_prodProds)
    st.dataframe(filtradosProductProds.applymap(lambda x: f"{x:.2e}"))
    filtradosTotalTiempo = productividadProds.loc["ProductividadMO (und/min)":"ProductividadMO (und/min)", departamento_selec].T.copy()
    filtradosTotalTiempo.index.name = "Productos"
    bar_chart_prodTiemp = px.bar(filtradosTotalTiempo, x=filtradosTotalTiempo.index, y=filtradosTotalTiempo.columns, template="plotly_white", title="Productividad MO (und/min)")
    st.plotly_chart(bar_chart_prodTiemp)
    st.dataframe(filtradosTotalTiempo)

    st.text("Indicadores de productividad parciales y totales de mano de obra y materia primar por estación")

    estaciones_selec = st.multiselect("Escoga las estaciones que desea ver",productividaEstaciones.columns.tolist(), default=productividaEstaciones.columns.tolist())
    filtradoEstundp = productividaEstaciones.loc["ProdMO (und/$)":"ProdMP+MO (und/$)", estaciones_selec].T
    filtradoEstundp.index.name = "Estación"
    barc_Estp = px.bar(filtradoEstundp, x=filtradoEstundp.index, y= filtradoEstundp.columns, template="plotly_white", title="Productividad en und/$ para cada estación", barmode="group")
    barc_Estp.layout.xaxis.dtick = 1
    st.plotly_chart(barc_Estp)
    st.dataframe(filtradoEstundp)

    filtradoEstt = productividaEstaciones.loc["ProdMO (und/min)":"ProdMO (und/min)", estaciones_selec].T
    filtradoEstt.index.name = "Estación"
    barc_estt = px.bar(filtradoEstt, x=filtradoEstt.index, y=filtradoEstt.columns, template="plotly_white", title="Productividad MO (und/min)")
    st.plotly_chart(barc_estt)
    st.dataframe(filtradoEstt)

    st.subheader(f"La productividad total de la empresa es de {round(prodTotal,2)} \$/\$")

    st.subheader(f"La utilidad total de la empresa mensual es de ${round(utilidadTotal,1):,}")

    st.header("A partir del analísis de la distribución de planta se encontró la siguiente solución que optimiza el layout de la compañia")
    st.image(r"https://res.cloudinary.com/camilo203/image/upload/v1633292308/ConfigOpti_cb4tnc.png")
    st.text("Matriz distancia configuraccón optimizada")
    
    

except:
    st.text_area("","No se ingreso un archivo valido, guiarse con el formato dado en el manual, recuerde que los datos deben estar en la primera hoja del excel")

try:
    (
        Productos,
        Estaciones,
        Recursos,
        MO,
        ManoDeObraMes,
        Gastos,
        CM,
        CostoMovimiento,
        Precios,
    ) = loadData(fileN) if fileN else loadData() 
    (
        productividadProds,
        productividaEstaciones,
        costosTotales,
        prodTotal,
        utilidadTotal,
        MatrizDistancia
    ) = procesarDatos(
        Productos, Estaciones, Recursos, ManoDeObraMes, Gastos, CostoMovimiento, Precios, r"https://res.cloudinary.com/camilo203/raw/upload/v1633292680/MatrizDOpti_cxs0dg.xlsx"
    )
    st.text("Matriz de distancia entre estaciones:")
    st.dataframe(MatrizDistancia)

    st.subheader("Los indicadores de productividad y costos son los siguientes: ")
    productos = Productos.Producto.to_list()
    departamento_selec = st.multiselect("Escoga de que productos desea ver los costos totales:", productos,key=[x+3 for x in range(16)], default=productos)

    st.text("Costos totales unitarios por producto")
    filtradosProds = costosTotales.loc["CostoTotalUnitario",departamento_selec] 
    filtradosProds.index.name = "Producto"
    bar_chart_costoProds = px.bar(filtradosProds,x=filtradosProds.index,y="CostoTotalUnitario", template="plotly_white")
    st.plotly_chart(bar_chart_costoProds)
    st.dataframe(filtradosProds)

    st.text("Rentabilidad Mensual de los productos")
    filtradosRentProds = costosTotales.loc["UtilidadMensual",departamento_selec] 
    filtradosRentProds.index.name = "Producto"
    bar_chart_rentProds = px.bar(filtradosRentProds,x=filtradosRentProds.index,y="UtilidadMensual", template="plotly_white")
    st.plotly_chart(bar_chart_rentProds)
    st.dataframe(filtradosRentProds)

    st.text("Indicadores de producitividad parciales y totales de mano de obra y materia prima por producto")
    filtradosProductProds = productividadProds.loc["ProductividadMP (und/$)":"ProductividadMO+MP (und/$)", departamento_selec].copy()
    filtradosProductProds = filtradosProductProds.T
    filtradosProductProds.index.name = "Productos"
    bar_chart_prodProds = px.bar(filtradosProductProds, x=filtradosProductProds.index, y =filtradosProductProds.columns ,barmode="group", template="plotly_white", title="Productividad (und/$) parciales y totales")
    bar_chart_prodProds.update_layout(yaxis_tickformat=".2e")
    st.plotly_chart(bar_chart_prodProds)
    st.dataframe(filtradosProductProds.applymap(lambda x: f"{x:.2e}"))
    filtradosTotalTiempo = productividadProds.loc["ProductividadMO (und/min)":"ProductividadMO (und/min)", departamento_selec].T.copy()
    filtradosTotalTiempo.index.name = "Productos"
    bar_chart_prodTiemp = px.bar(filtradosTotalTiempo, x=filtradosTotalTiempo.index, y=filtradosTotalTiempo.columns, template="plotly_white", title="Productividad MO (und/min)")
    st.plotly_chart(bar_chart_prodTiemp)
    st.dataframe(filtradosTotalTiempo)

    st.text("Indicadores de productividad parciales y totales de mano de obra y materia primar por estación")

    estaciones_selec = st.multiselect("Escoga las estaciones que desea ver",productividaEstaciones.columns.tolist(),key=[x+4 for x in range(13)] ,default=productividaEstaciones.columns.tolist())
    filtradoEstundp = productividaEstaciones.loc["ProdMO (und/$)":"ProdMP+MO (und/$)", estaciones_selec].T
    filtradoEstundp.index.name = "Estación"
    barc_Estp = px.bar(filtradoEstundp, x=filtradoEstundp.index, y= filtradoEstundp.columns, template="plotly_white", title="Productividad en und/$ para cada estación", barmode="group")
    barc_Estp.layout.xaxis.dtick = 1
    st.plotly_chart(barc_Estp)
    st.dataframe(filtradoEstundp)

    filtradoEstt = productividaEstaciones.loc["ProdMO (und/min)":"ProdMO (und/min)", estaciones_selec].T
    filtradoEstt.index.name = "Estación"
    barc_estt = px.bar(filtradoEstt, x=filtradoEstt.index, y=filtradoEstt.columns, template="plotly_white", title="Productividad MO (und/min)")
    st.plotly_chart(barc_estt)
    st.dataframe(filtradoEstt)

    st.subheader(f"La productividad total de la empresa es de {round(prodTotal,2)} \$/\$")

    st.subheader(f"La utilidad total de la empresa mensual es de ${round(utilidadTotal,1):,}")
except:
    pass