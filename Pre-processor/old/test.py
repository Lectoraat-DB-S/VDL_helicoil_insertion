import gmsh
import numpy as np

def get_stepped_hole_properties(step_file):
    gmsh.initialize()
    try:
        gmsh.model.occ.importShapes(step_file)
        gmsh.model.occ.synchronize()

        raw_cylinders = []
        surfaces = gmsh.model.getEntities(2)

        #Search all surfaces for cylinders. Note each hole consists of two surfaces (half circumference of cylinder)
        for dim, tag in surfaces:
            if "Cylind" in gmsh.model.getType(dim, tag):
                bounds = gmsh.model.getParametrizationBounds(dim, tag)
                u_min, u_max = bounds[0][0], bounds[1][0]  #u_min and u_max containt the rotation around the cylinder axis, 0 to pi for half a cylinder, or pi to 2*pi
                v_min, v_max = bounds[0][1], bounds[1][1]  #v_min and v_max containt the length along the cylinder axis

                #used to generate two point on the cylinder. In this case, used for each corner of the cylinder
                def get_circle_data(v_val):
                    pts = [gmsh.model.getValue(dim, tag, [u_min + (u_max - u_min) * (i / float(2)), v_val]) 
                           for i in range(2)]
                    pts = np.array(pts)
                    center = np.mean(pts, axis=0)
                    radius = np.mean(np.linalg.norm(pts - center, axis=1))
                    return center, radius

                # Four corners of cylinder surface
                c_start, r_start = get_circle_data(v_min)
                c_end, r_end = get_circle_data(v_max)
                
                # Calculate Length and Directional Axis
                vec = c_end - c_start
                length = np.linalg.norm(vec)

                # Avoid division by zero for degenerate cylinders
                axis = vec / length if length > 1e-9 else np.array([0.0, 0.0, 0.0])       
                
                
                raw_cylinders.append({
                    "tag": tag,
                    "c1": c_start,
                    "c2": c_end,
                    "radius": r_start,
                    "length": length,
                    "axis": axis
                })

        # Find cylinders at same location (2 at single location)
        holes = []
        used_tags = set()

        for i, cyl1 in enumerate(raw_cylinders):
            if cyl1["tag"] in used_tags: continue
            
            current_hole = [cyl1]
            used_tags.add(cyl1["tag"])

            for j, cyl2 in enumerate(raw_cylinders):
                if i == j or cyl2["tag"] in used_tags: continue
                dists = [np.linalg.norm(cyl1["c1"] - cyl2["c1"]), np.linalg.norm(cyl1["c1"] - cyl2["c2"]),
                         np.linalg.norm(cyl1["c2"] - cyl2["c1"]), np.linalg.norm(cyl1["c2"] - cyl2["c2"])]
                if min(dists) < 1e-6:  #search for cylinders with distance between center points is very small. Note start and end side can be swapped
                    current_hole.append(cyl2)
                    used_tags.add(cyl2["tag"])

            # Clean output conversion (removing np.float and ndarray issues when printing)
            total_lengths = [float(c["length"]) for c in current_hole]
            radii = [float(c["radius"]) for c in current_hole]
            
            # The axis of the first segment usually represents the whole hole direction
            main_axis = current_hole[0]["axis"].tolist()
            
            c1_set = np.array([c["c1"] for c in current_hole])
            c2_set = np.array([c["c2"] for c in current_hole])
            center_avg = ((np.mean(c1_set, axis=0) + np.mean(c2_set, axis=0)) / 2).tolist()

            holes.append({
                "segments": len(current_hole),
                "surface_tags": [int(c["tag"]) for c in current_hole],
                "center": center_avg,
                "axis": main_axis,
                "radii": radii,
                "total_length": total_lengths
            })

        return holes

    finally:
        gmsh.finalize()

# --- Execution ---
hole_systems = get_stepped_hole_properties("Pre-processor/Testobject/achterplaat.step")
for h in hole_systems:
    # Use np.round and tolist() to keep printing clean
    clean_center = [round(x, 3) for x in h['center']]
    clean_axis = [round(x, 3) for x in h['axis']]
    clean_radii = [round(r, 3) for r in h['radii']]
    
    print(f"Hole tags: {h['surface_tags']}")
    print(f"  Center: {clean_center}")
    print(f"  Direction (Axis): {clean_axis}")
    print(f"  Radii: {clean_radii}")
    print(f"  Lengths: {h['total_length']}")