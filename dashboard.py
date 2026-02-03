import vizro.plotly.express as px
from vizro import Vizro
import vizro.models as vm

# Load sample data (you can replace this with your own data)
df = px.data.iris()

# Create a page with components
page = vm.Page(
    title="My first dashboardz",
    components=[
        vm.Graph(figure=px.scatter(df, x="sepal_length", y="petal_width", color="species")),
        vm.Graph(figure=px.histogram(df, x="sepal_width", color="species"))
    ],
    controls=[
        vm.Filter(column="species"),
    ],
)

# Create the dashboard
dashboard = vm.Dashboard(pages=[page])

# Build and run
if __name__ == "__main__":
    Vizro().build(dashboard).run()